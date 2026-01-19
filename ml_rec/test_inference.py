# ml_rec/inference.py
# 아직 모델은 없지만, 마치 있는 척하는 연기(Mocking)를 한다.

def get_recommendations(user_id: int):
    print(f"== [ML_Log] 유저 {user_id}를 위한 추론 시작... ==")
    # 복잡한 모델 연산 대신 고정된 값 리턴
    return [101, 102, 103, 777, 999]