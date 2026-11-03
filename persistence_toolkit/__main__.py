from .comparison import compare_reports,render_markdown,summarize_seed_runs
import argparse,json,pathlib

def main():
    p=argparse.ArgumentParser(description="Standalone, descriptive comparison; not the published audit engine")
    sp=p.add_subparsers(dest="mode",required=True)
    q=sp.add_parser("compare");q.add_argument("left");q.add_argument("right");q.add_argument("--out",required=True)
    z=sp.add_parser("seeds");z.add_argument("inputs");z.add_argument("--out",required=True)
    args=p.parse_args()
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if args.mode=="compare":
        L=json.loads(pathlib.Path(args.left).read_text());R=json.loads(pathlib.Path(args.right).read_text())
        result=compare_reports(L,R)
        (out/"comparison_report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        (out/"comparison_report.md").write_text(render_markdown(result))
    else:
        records=json.loads(pathlib.Path(args.inputs).read_text())
        (out/"seed_variability.json").write_text(json.dumps(summarize_seed_runs(records),indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
