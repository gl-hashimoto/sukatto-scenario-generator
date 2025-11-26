#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改行処理のテストスクリプト
"""

import re

def enforce_line_breaks(text):
    """
    シナリオテキストの改行を強制的に修正する
    ※カメラ、※状況、セリフ、心の声をそれぞれ別の行に分離
    """
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        # コマ番号やページ番号、区切り線はそのまま
        stripped = line.strip()
        if (stripped.startswith(('【', '■', '━', '※前編', '※後編')) or 
            stripped in ['1コマ目', '2コマ目', '3コマ目', '4コマ目', '5コマ目', '6コマ目'] or
            re.match(r'^\d+コマ目', stripped) or
            stripped.startswith('**') and 'コマ目' in stripped):
            result_lines.append(line)
            continue
        
        # 空行はそのまま
        if not stripped:
            result_lines.append(line)
            continue
        
        # 既に正しく改行されている行（※だけ、セリフだけ、心の声だけ）はそのまま
        if (stripped.startswith('※') and '「' not in line and '（' not in line) or \
           (re.match(r'^[A-Z][子男]「[^」]*」$', stripped) and '※' not in line) or \
           (re.match(r'^[A-Z][子男]（[^）]*）$', stripped) and '※' not in line):
            result_lines.append(line)
            continue
        
        # 複数の要素が混在している行を処理
        # パターンを抽出
        elements = []
        
        # ※で始まる部分を抽出（より正確に）
        # ※から次の※、または「、または（まで
        pos = 0
        while pos < len(line):
            if line[pos] == '※':
                start = pos
                pos += 1
                # 次の※、または「、または（まで探す
                while pos < len(line) and line[pos] not in ['※', '「', '（']:
                    pos += 1
                end = pos
                content = line[start:end].strip()
                if content:
                    elements.append(('camera', start, end, content))
            else:
                pos += 1
        
        # セリフを抽出
        dialogue_pattern = r'[A-Z][子男]「[^」]*」'
        dialogue_matches = list(re.finditer(dialogue_pattern, line))
        for match in dialogue_matches:
            elements.append(('dialogue', match.start(), match.end(), match.group().strip()))
        
        # 心の声を抽出
        thought_pattern = r'[A-Z][子男]（[^）]*）'
        thought_matches = list(re.finditer(thought_pattern, line))
        for match in thought_matches:
            elements.append(('thought', match.start(), match.end(), match.group().strip()))
        
        # 要素を位置順にソート
        elements.sort(key=lambda x: x[1])
        
        if len(elements) > 1:
            # 複数の要素がある場合、それぞれを別の行に
            for elem_type, start, end, content in elements:
                if content:
                    result_lines.append(content)
        elif len(elements) == 1:
            # 1つの要素だけなら、その要素を抽出
            _, _, _, content = elements[0]
            if content:
                result_lines.append(content)
        else:
            # 要素が見つからない場合はそのまま
            result_lines.append(line)
    
    return '\n'.join(result_lines)

# テストケース
test_cases = [
    # ケース1: 改行されていない行
    "※カメラ：引き※リビングA子「こんにちは」A子（心の声）",
    # ケース2: 部分的に改行されている
    "※カメラ：引き※リビング\nA子「こんにちは」A子（心の声）",
    # ケース3: セリフが複数
    "A子「セリフ1」A子「セリフ2」",
    # ケース4: 既に正しく改行されている
    "※カメラ：引き\n※リビング\nA子「こんにちは」\nA子（心の声）",
]

print("=" * 60)
print("改行処理のテスト")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    print(f"\n【テストケース {i}】")
    print("入力:")
    print(repr(test))
    print("\n出力:")
    result = enforce_line_breaks(test)
    print(result)
    print("\n" + "-" * 60)

