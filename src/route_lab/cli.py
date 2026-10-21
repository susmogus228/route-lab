"""Command-line route solving, repeatable measurements and local preview."""
import argparse
import csv
import json
from pathlib import Path
import sys

from .core import ValidationError
from .service import compare, solve


def strict_json_loads(text: str):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:
                raise ValueError(f'Duplicate JSON field: {key}.')
            result[key]=value
        return result
    def invalid_constant(value):
        raise ValueError(f'Nonfinite JSON number is not accepted: {value}.')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid_constant)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='route-lab',description='Weighted-grid shortest paths and reproducible algorithm comparison.')
    commands=parser.add_subparsers(dest='command',required=True)
    route=commands.add_parser('solve',help='Solve a scenario JSON file.')
    route.add_argument('--input',type=Path,required=True)
    route.add_argument('--algorithm',choices=('astar','dijkstra'))
    route.add_argument('--trace-limit',type=int)
    route.add_argument('--output',type=Path)
    route.add_argument('--path-csv',type=Path)
    route.add_argument('--compare',action='store_true')
    bench=commands.add_parser('benchmark',help='Run the saved synthetic-map timing protocol.')
    bench.add_argument('--output',type=Path,default=Path('results'))
    bench.add_argument('--sizes',default='32,64,128')
    bench.add_argument('--seeds',default='11,22,33,44,55')
    bench.add_argument('--repeats',type=int,default=5)
    demo=commands.add_parser('demo',help='Serve the local interactive application.')
    demo.add_argument('--results',type=Path,default=Path('results'))
    demo.add_argument('--port',type=int,default=8767)
    args=parser.parse_args(argv)
    try:
        if args.command=='demo':
            from .demo import serve
            serve(args.results,args.port)
            return 0
        if args.command=='benchmark':
            from .benchmark import run_benchmark
            result=run_benchmark(args.output,tuple(map(int,args.sizes.split(','))),tuple(map(int,args.seeds.split(','))),args.repeats)
            print(json.dumps({'output':str(args.output.resolve()),'cases':len(result['rows'])//2,'timed_runs':len(result['measurements'])}))
            return 0
        destinations=[path.resolve() for path in (args.output,args.path_csv) if path is not None]
        if args.input.resolve() in destinations or len(destinations)!=len(set(destinations)):
            raise ValueError('Output paths must differ from the input and from each other.')
        if args.input.stat().st_size>262144:
            raise ValueError('Scenario JSON exceeds the 256 KiB file limit.')
        payload=strict_json_loads(args.input.read_text(encoding='utf-8-sig'))
        if not isinstance(payload,dict):
            raise ValidationError('Scenario must be a JSON object.')
        if args.algorithm:
            if args.compare:
                raise ValueError('--algorithm and --compare cannot be combined.')
            payload['algorithm']=args.algorithm
        if args.trace_limit is not None:
            payload['trace_limit']=args.trace_limit
        result=compare(payload) if args.compare else solve(payload)
        encoded=json.dumps(result,indent=2,allow_nan=False)+'\n'
        if args.path_csv:
            if args.compare:
                raise ValueError('--path-csv requires one algorithm; omit --compare.')
            cumulative=0
            with args.path_csv.open('w',encoding='utf-8',newline='') as stream:
                writer=csv.writer(stream)
                writer.writerow(['step','row','column','entry_cost','cumulative_cost'])
                for step,(r,c) in enumerate(result['path']):
                    entry=0 if step==0 else payload['grid'][r][c]
                    cumulative+=entry
                    writer.writerow([step,r,c,entry,cumulative])
        if args.output:
            args.output.write_text(encoded,encoding='utf-8')
        print(encoded,end='')
        return 0
    except (OSError,ValueError) as exc:
        print(f'route-lab: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
