import json
import csv

def convert_steam_data(input_path, output_path):
    """
    steamDB_crawling.jsonl 파일을 RecBole의 입력 형식으로 변환합니다.

    Args:
        input_path (str): 원본 steamDB_crawling.jsonl 파일 경로
        output_path (str): 변환된 데이터가 저장될 .inter 파일 경로
    """
    print(f"변환 시작: {input_path} -> {output_path}")

    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        
        writer = csv.writer(outfile)
        # RecBole에서 인식할 헤더 작성
        writer.writerow(['user_id:token', 'item_id:token', 'rating:float'])

        for i, line in enumerate(infile):
            try:
                data = json.loads(line)
                user_id = data.get('steamid')
                games = data.get('games', [])

                if not user_id or not games:
                    continue

                for game in games:
                    item_id = game.get('appid')
                    if item_id:
                        # user_id, item_id, rating(암시적 데이터이므로 1)
                        writer.writerow([user_id, item_id, 1])
                
                if (i + 1) % 10000 == 0:
                    print(f"{i + 1}번째 줄 처리 완료...")

            except json.JSONDecodeError:
                print(f"JSON 디코딩 오류 발생: {i+1}번째 줄")
                continue

    print("변환 완료!")

if __name__ == '__main__':
    # 입력 및 출력 파일 경로 설정
    # 이 스크립트는 steam_project/scripts/ 폴더에 위치한다고 가정합니다.
    input_file = './dataset/steam/steamDB_crawling.jsonl'
    output_file = './dataset/steam/steam_data.inter'
    
    convert_steam_data(input_file, output_file)