#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
過去に生成されたシナリオの改行を修正するスクリプト
"""

import os
import json
import re
from pathlib import Path

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
            re.match(r'^\d+コマ目', stripped)):
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
        
        # ※で始まる部分を抽出
        camera_pattern = r'※[^※「（]+'
        camera_matches = list(re.finditer(camera_pattern, line))
        for match in camera_matches:
            elements.append(('camera', match.start(), match.end(), match.group().strip()))
        
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

def fix_scenario_file(filepath):
    """
    1つのシナリオファイルを修正
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_result = data.get('result', '')
        if not original_result:
            return False
        
        # 改行を修正
        fixed_result = enforce_line_breaks(original_result)
        
        # 変更があったかチェック
        if original_result == fixed_result:
            return False
        
        # ファイルを更新
        data['result'] = fixed_result
        data['fixed_line_breaks'] = True
        data['fixed_at'] = datetime.now().isoformat()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"エラー: {filepath} - {str(e)}")
        return False

def main():
    """
    過去の生成物をすべて修正
    """
    output_dir = Path(__file__).parent / "output"
    
    if not output_dir.exists():
        print("outputディレクトリが見つかりません")
        return
    
    # JSONファイルを取得
    json_files = list(output_dir.glob("scenario_*.json"))
    
    if not json_files:
        print("修正対象のファイルが見つかりません")
        return
    
    print(f"見つかったファイル数: {len(json_files)}")
    
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for filepath in json_files:
        print(f"処理中: {filepath.name}...", end=" ")
        try:
            if fix_scenario_file(filepath):
                print("✓ 修正完了")
                fixed_count += 1
            else:
                print("- 変更なし")
                skipped_count += 1
        except Exception as e:
            print(f"✗ エラー: {str(e)}")
            error_count += 1
    
    print("\n" + "="*50)
    print(f"処理完了:")
    print(f"  修正: {fixed_count}件")
    print(f"  変更なし: {skipped_count}件")
    print(f"  エラー: {error_count}件")
    print("="*50)

if __name__ == "__main__":
    from datetime import datetime
    main()

