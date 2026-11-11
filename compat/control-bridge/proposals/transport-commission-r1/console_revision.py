"""Print a narrow proposed integration diff; never change active source/runtime."""
from pathlib import Path
import difflib
import sys


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Exact console proposal context changed; review instead of a broad rewrite')
    return source.replace(old, new, 1)


def server_revision(source):
    source = once(source,
        '                     r"awftmill (inspect|commission) mill-commission-[a-f0-9]{16} [a-f0-9]{64}",\n', '')
    source = once(source, "'awftmill resume ')):", "'awftmill inspect ', 'awftmill resume ')):")
    return once(source, r'awftmill resume mill-commission-[a-f0-9]{16} [a-f0-9]{64}',
                r'awftmill (inspect|resume) mill-resume-[a-f0-9]{16} [a-f0-9]{64}')


def tests_revision(source):
    source = once(source, 'def test_mill_commissioning_requires_confirmation_and_typed_bundle(self):',
                  'def test_retained_mill_resume_requires_confirmation_and_typed_bundle(self):')
    source = once(source, "        command = 'awftmill commission mill-commission-1234567890abcdef ' + 'b' * 64",
        "        write_json(self.layout.state / 'artistic-owner.json',\n"
        "                   {'format': 'awft-artistic-stage:1', 'home': str(self.layout.home)})\n"
        "        self.layout.save_settings(self.layout.settings() | {'permanent_world': False, 'port': 25575})\n"
        "        command = 'awftmill resume mill-resume-1234567890abcdef ' + 'b' * 64")
    source = once(source, "command.replace('mill-commission-', '../')", "command.replace('mill-resume-', '../')")
    return once(source, "('awftmill', 'resume', 'inspect', 'mill-commission-')",
                "('awftmill', 'resume', 'inspect', 'mill-resume-')")


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[4]
    for relative, revision in (('control_room/server.py', server_revision), ('tests/test_safety.py', tests_revision)):
        source = (root/relative).read_text(encoding='utf8')
        diff=''.join(difflib.unified_diff(source.splitlines(True), revision(source).splitlines(True),
                                        fromfile='a/'+relative, tofile='b/'+relative))
        sys.stdout.buffer.write(diff.encode('utf8'))
