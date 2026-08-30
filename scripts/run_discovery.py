from pathlib import Path

source_path = Path(__file__).with_name('build_discovery.py')
source = source_path.read_text(encoding='utf-8')

# Compatibility repair for the first multilingual discovery template release.
# The repair is deterministic and idempotent: if the source is corrected later,
# this pattern no longer matches and no mutation is applied.
broken = "\n}\n\nVI_KEYWORDS = ["
fixed = "\n}\n}\n\nVI_KEYWORDS = ["
if broken in source and fixed not in source:
    source = source.replace(broken, fixed, 1)

code = compile(source, str(source_path), 'exec')
namespace = {'__file__': str(source_path), '__name__': '__main__'}
exec(code, namespace, namespace)
