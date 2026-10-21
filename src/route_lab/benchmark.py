"""Saved, repeated measurements on original synthetic maps."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys

from .core import search, validate

PROTOCOL = {
    "schema_version": 1,
    "sizes": [32, 64, 128],
    "seeds": [11, 22, 33, 44, 55],
    "families": ["open_uniform", "open_weighted", "blocked_weighted"],
    "repeats": 5,
    "warmup_per_algorithm": 1,
    "trace_limit": 0,
    "blocked_probability": 0.25,
    "corridor": "top row and rightmost column stay open; all maps have a route",
    "timing": "search perf_counter_ns including reconstruction, excluding validation and serialization",
    "run_order": "alternate dijkstra/astar order each repetition and case",
    "tie_order": "priority f, heuristic h, insertion serial; neighbors up/right/down/left",
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def generate_scenario(size: int, seed: int, family: str) -> dict:
    if type(size) is not int or not 1 <= size <= 128 or type(seed) is not int:
        raise ValueError("Size must be an integer 1..128 and seed an integer.")
    if family not in PROTOCOL["families"]:
        raise ValueError("Unknown benchmark map family.")
    rng = random.Random(seed)
    grid = [[1 if family == "open_uniform" else rng.randint(1,9) for _ in range(size)] for _ in range(size)]
    if family == "blocked_weighted":
        for r in range(1,size):
            for c in range(size-1):
                if rng.random() < PROTOCOL["blocked_probability"]:
                    grid[r][c] = 0
    grid[0][0] = grid[-1][-1] = 1
    return {"grid":grid,"start":[0,0],"goal":[size-1,size-1]}


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot(path: Path, rows: list[dict]) -> None:
    """Self-contained scientific SVG: aggregate medians, no external assets."""
    sizes = sorted({row["size"] for row in rows})
    families = PROTOCOL["families"]
    height = 130 + len(families) * (45 + 42 * len(sizes))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">RouteLab measured search time by map family</title>',
        '<desc id="desc">Bars show the median across scenario timing medians. Each scenario has at least five measured runs. Runtime depends on the machine and generated maps.</desc>',
        '<rect width="960" height="100%" fill="#fff"/>',
        '<g font-family="system-ui, sans-serif" fill="#171717">',
        '<text x="32" y="36" font-size="23" font-weight="700">RouteLab: recorded search time</text>',
        '<text x="32" y="61" font-size="13">Median of per-map medians (ms); trace disabled. Dijkstra gray; A* blue.</text>']
    y = 95
    for family in families:
        parts.append(f'<text x="32" y="{y}" font-size="17" font-weight="600">{family.replace("_"," ")}</text>')
        summaries = {(size,algo): statistics.median([row['median_ms'] for row in rows if row['family']==family and row['size']==size and row['algorithm']==algo]) for size in sizes for algo in ('dijkstra','astar')}
        scale = 650/max(summaries.values(),default=1) if max(summaries.values(),default=0)>0 else 1
        y += 20
        for size in sizes:
            parts.append(f'<text x="32" y="{y+16}" font-size="13">{size} x {size}</text>')
            for offset,algo,color in ((0,'dijkstra','#666666'),(17,'astar','#0969da')):
                value=summaries[(size,algo)]
                width=max(1,value*scale)
                parts.append(f'<rect x="145" y="{y+offset}" width="{width:.2f}" height="13" fill="{color}"/>')
                parts.append(f'<text x="{153+width:.2f}" y="{y+offset+11}" font-size="11">{value:.3f}</text>')
            y += 42
        y += 25
    parts.append(f'<text x="32" y="{height-17}" font-size="12">Original synthetic maps; guaranteed corridor. No universal speedup claim. See raw CSV and protocol.</text></g></svg>')
    path.write_text('\n'.join(parts),encoding='utf-8')


def run_benchmark(output: Path, sizes=(32,64,128), seeds=(11,22,33,44,55), repeats=5) -> dict:
    if type(repeats) is not int or not 5 <= repeats <= 100:
        raise ValueError("Benchmark needs 5 through 100 measured repetitions.")
    sizes, seeds = tuple(sizes), tuple(seeds)
    if not sizes or not seeds or len(sizes)>10 or len(seeds)>20 or len(set(sizes))!=len(sizes) or len(set(seeds))!=len(seeds):
        raise ValueError("Provide nonempty unique sizes and seeds (at most 10 and 20).")
    for size in sizes:
        for seed in seeds:
            generate_scenario(size,seed,'open_uniform')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/'scenarios').mkdir(exist_ok=True)
    configuration={**PROTOCOL,'sizes':list(sizes),'seeds':list(seeds),'repeats':repeats}
    (output/'protocol.json').write_bytes(canonical_bytes(configuration))
    source_files={file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(Path(__file__).parent.glob('*.py')) if file.name not in ('demo.py','cli.py','__main__.py')}
    source_hash=hashlib.sha256(canonical_bytes(source_files)).hexdigest()
    rows, measurements = [], []
    case_number = 0
    for family in PROTOCOL['families']:
        for size in sizes:
            for seed in seeds:
                case_id=f'{family}-{size}-seed-{seed}'
                payload=generate_scenario(size,seed,family)
                scenario_bytes=canonical_bytes(payload)
                (output/'scenarios'/f'{case_id}.json').write_bytes(scenario_bytes)
                scenario,_,_=validate(payload)
                warm={name:search(scenario,name,0) for name in ('dijkstra','astar')}
                if (warm['dijkstra']['reachable'],warm['dijkstra']['cost']) != (warm['astar']['reachable'],warm['astar']['cost']):
                    raise RuntimeError('Algorithm cost disagreement: '+case_id)
                recorded={'dijkstra':[],'astar':[]}
                for repeat in range(repeats):
                    order=('dijkstra','astar') if (repeat+case_number)%2==0 else ('astar','dijkstra')
                    for position,name in enumerate(order):
                        result=search(scenario,name,0)
                        if result['cost']!=warm[name]['cost'] or result['expanded']!=warm[name]['expanded']:
                            raise RuntimeError('Nondeterministic solve: '+case_id)
                        recorded[name].append(result['runtime_ms'])
                        measurements.append({'case_id':case_id,'algorithm':name,'repeat':repeat+1,'position':position+1,'runtime_ms':result['runtime_ms']})
                for name in ('dijkstra','astar'):
                    result=warm[name]
                    times=recorded[name]
                    rows.append({'case_id':case_id,'family':family,'size':size,'seed':seed,'algorithm':name,'reachable':result['reachable'],'cost':result['cost'],'steps':result['steps'],'expanded':result['expanded'],'heap_peak':result['heap_peak'],'median_ms':statistics.median(times),'min_ms':min(times),'max_ms':max(times),'raw_ms':times,'scenario_sha256':hashlib.sha256(scenario_bytes).hexdigest(),'blocked_cells':sum(v==0 for row in payload['grid'] for v in row),'cost_histogram':{str(v):sum(x==v for row in payload['grid'] for x in row) for v in range(10)}})
                case_number+=1
    result={'schema_version':1,'kind':'recorded_benchmark','live_benchmark':False,'created_at_utc':datetime.now(timezone.utc).isoformat(),'configuration':configuration,'source_sha256':source_hash,'source_files':source_files,'protocol_sha256':hashlib.sha256(canonical_bytes(configuration)).hexdigest(),'environment':{'python':sys.version,'platform':platform.platform(),'processor':platform.processor()},'rows':rows,'measurements':measurements,'limitations':['Original synthetic grids with a reserved corridor; real navigation not evaluated.','Five repeated timings measure this process and machine; other workloads may behave differently.','A* is not guaranteed faster. heap_peak counts raw queue entries, including stale entries.']}
    (output/'benchmark.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    _write_csv(output/'benchmark.csv',[{k:v for k,v in row.items() if k not in ('raw_ms','cost_histogram')} for row in rows])
    _write_csv(output/'benchmark-raw.csv',measurements)
    _plot(output/'benchmark.svg',rows)
    lines=['# RouteLab recorded benchmark','',f'{case_number} synthetic scenarios; {len(measurements)} timed runs; {repeats} repetitions per algorithm after one warmup.','', 'All recorded Dijkstra and A* costs agree. Timings exclude validation and serialization; trace capture is disabled.','', '| Family | Size | Dijkstra median ms | A* median ms |','|---|---:|---:|---:|']
    for family in PROTOCOL['families']:
        for size in sizes:
            values=[statistics.median([r['median_ms'] for r in rows if r['family']==family and r['size']==size and r['algorithm']==name]) for name in ('dijkstra','astar')]
            lines.append(f'| {family} | {size} | {values[0]:.3f} | {values[1]:.3f} |')
    lines.extend(['','Table values are medians across per-map timing medians. Inspect per-seed rows and all raw measurements before interpreting the aggregate.','', 'A* can expand fewer nodes while spending time on heuristic calculations. These results establish measured behavior on the saved fixtures, not a universal ranking.','', '![Recorded benchmark](benchmark.svg)',''])
    (output/'benchmark.md').write_text('\n'.join(lines),encoding='utf-8')
    return result
