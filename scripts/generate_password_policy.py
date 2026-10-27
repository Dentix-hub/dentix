"""Generate browser policy data from backend constants and Python character rules.

Run after changing backend policy constants; parity tests detect stale output.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def character_ranges(predicate):
    ranges = []
    for code in range(0x110000):
        if predicate(chr(code)):
            if ranges and code == ranges[-1][1] + 1:
                ranges[-1][1] = code
            else:
                ranges.append([code, code])
    return ranges


def policy_data():
    tree = ast.parse((ROOT / 'backend/routers/auth/dependencies.py').read_text())
    constants = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and target.id in {
                'PASSWORD_MIN_LENGTH', 'PASSWORD_MAX_LENGTH', 'COMMON_WEAK_PASSWORDS',
            }:
                value = node.value.args[0] if isinstance(node.value, ast.Call) else node.value
                constants[target.id] = ast.literal_eval(value)
    data = {
        'minLength': constants['PASSWORD_MIN_LENGTH'],
        'maxLength': constants['PASSWORD_MAX_LENGTH'],
        'weakPasswords': sorted(constants['COMMON_WEAK_PASSWORDS']),
        'letterRanges': character_ranges(str.isalpha),
        'digitRanges': character_ranges(str.isdigit),
        'whitespace': ''.join(chr(code) for code in range(0x110000) if chr(code).isspace()),
    }
    return data


if __name__ == '__main__':
    target = ROOT / 'frontend/src/auth/passwordPolicyData.json'
    target.write_text(json.dumps(policy_data(), ensure_ascii=True, separators=(',', ':')) + '\n')
