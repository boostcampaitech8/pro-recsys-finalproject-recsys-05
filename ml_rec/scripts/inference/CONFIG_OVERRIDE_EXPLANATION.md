# 🔧 Config 덮어쓰기 메커니즘 설명

## 📌 핵심 개념

**RecBole의 설정 우선순위:**

```
1. YAML 파일 (초기 설정)
        ↓
2. Python 코드 (동적 덮어쓰기) ← 더 높은 우선순위!
        ↓
3. 최종 설정 (Python이 YAML을 덮어씀)
```

---

## 🎯 실제 예제

### YAML 설정 (recbole_config_ease.yaml)

```yaml
eval_args:
  split: {'RS': [0.8, 0.1, 0.1]}
  group_by: user
  order: RO
  mode: uni100  # ← 정답 1개 + 오답 100개만

valid_sample_rate: 0.1  # ← 검증 데이터 10% 샘플링
```

### Python 코드 (evaluate_model_full.py)

```python
# Line 107-117: YAML 설정을 완전히 덮어쓰기
eval_args = {
    'mode': 'full',  # ← uni100을 'full'로 변경
    'order': 'RO',
}

config['eval_args'] = eval_args
config['topk'] = [10, 20]
config['metrics'] = ['Recall', 'NDCG', 'MRR', 'Hit', 'Precision']
config['valid_sample_rate'] = 1.0  # ← 0.1을 1.0으로 변경
config['test_sample_rate'] = 1.0   # ← 새로 추가
```

### 결과

```
YAML의 uni100과 0.1 샘플링 설정은 완전히 무시되고,
Python 코드의 'full' 모드와 1.0 샘플링으로 평가됩니다.
```

---

## 🔍 왜 이런 메커니즘이 존재하는가?

### 장점

1. **재사용성**: 같은 YAML 파일을 여러 용도로 사용 가능
   ```python
   # 빠른 평가용 (YAML 그대로 사용)
   run_recbole(model='EASE', config_file_list=[...])

   # 정확한 평가용 (Python에서 덮어쓰기)
   config['eval_args'] = {'mode': 'full'}
   ```

2. **유연성**: 코드에서 동적으로 설정 변경 가능
   ```python
   if full_evaluation:
       config['valid_sample_rate'] = 1.0
   else:
       config['valid_sample_rate'] = 0.1
   ```

3. **원본 보존**: YAML 파일을 수정할 필요 없음
   ```python
   # YAML 건드리지 않고도 설정 변경
   config['eval_args']['mode'] = 'full'
   ```

---

## 📊 비교표

| 항목 | YAML (uni100) | Python (Full) | 설명 |
|------|---------------|---------------|------|
| **Mode** | uni100 | full | 평가 방식 |
| **Valid Sample** | 0.1 (10%) | 1.0 (100%) | 검증 데이터 사용량 |
| **Test Sample** | 0.1 (10%) | 1.0 (100%) | 테스트 데이터 사용량 |
| **평가 아이템** | 정답 1개 + 오답 100개 | 정답 1개 + 모든 오답 | 평가 대상 |
| **속도** | 빠름 (55분) | 느림 (2-4시간) | 소요 시간 |
| **정확도** | 근사값 | 정확한 값 | 평가 정확도 |

---

## 🎬 실행 흐름 상세

```python
# Step 1: YAML 로드
config = Config(model='EASE', config_file_list=['recbole_config_ease.yaml'])
# config['eval_args']['mode'] = 'uni100' (YAML에서 읽음)
# config['valid_sample_rate'] = 0.1 (YAML에서 읽음)

# Step 2: Python에서 덮어쓰기
eval_args = {'mode': 'full', 'order': 'RO'}
config['eval_args'] = eval_args
# config['eval_args']['mode'] = 'full' ← 변경됨!

config['valid_sample_rate'] = 1.0
# config['valid_sample_rate'] = 1.0 ← 변경됨!

# Step 3: Evaluator 생성 (변경된 config 사용)
evaluator = Evaluator(config)
# 이제 evaluator는 'full' 모드와 1.0 샘플링으로 작동
```

---

## ⚠️ 주의사항

### 1. 부분 덮어쓰기 주의

```python
# ❌ 위험: eval_args의 일부만 수정 (다른 항목은 남아있음)
config['eval_args']['mode'] = 'full'
# 이 경우 eval_args의 다른 항목들(split, group_by)은 그대로

# ✅ 권장: eval_args 전체를 교체
config['eval_args'] = {
    'mode': 'full',
    'order': 'RO',
}
```

### 2. 설정 검증 필수

```python
# 실제로 바뀌었는지 확인
print(f"Mode: {config['eval_args']['mode']}")
print(f"Valid Sample Rate: {config.get('valid_sample_rate', 1.0)}")
```

### 3. 성능 영향

```python
# full 모드는 메모리와 시간을 많이 사용
# GPU 메모리 부족 시:
config['eval_batch_size'] = 512  # 기본값: 2048로 줄이기
```

---

## 📈 평가 결과 비교 예상

### uni100 (YAML 설정)
```
Valid NDCG@10: 0.4652 ← 10% 데이터로 평가
Valid Recall@10: 0.4504
```

### Full (Python 덮어쓰기)
```
Valid NDCG@10: 0.4629 (예상) ← 100% 데이터로 평가
Valid Recall@10: 0.4481 (예상)
```

*Full 모드가 더 정확하므로 실제 성능에 더 가깝습니다.*

---

## 🚀 활용 팁

### Tip 1: 여러 설정으로 평가

```python
# 설정 A: 빠른 평가 (uni100)
run_recbole(model='EASE', config_file_list=['config.yaml'])

# 설정 B: 정확한 평가 (full)
config['eval_args']['mode'] = 'full'
config['valid_sample_rate'] = 1.0
evaluator = Evaluator(config)
```

### Tip 2: 하이브리드 평가

```python
# 검증: 빠른 평가 (uni100)로 개발 중 모니터링
# 최종: 정확한 평가 (full)로 최종 성능 측정

if production:
    config['eval_args']['mode'] = 'full'
    config['valid_sample_rate'] = 1.0
```

### Tip 3: 조정 가능한 평가

```python
# 중간 속도와 정확도 타협
config['eval_args']['mode'] = 'uni1000'  # 정답 1개 + 오답 1000개
config['valid_sample_rate'] = 0.5        # 50% 데이터 사용
```

---

## 📝 정리

| 질문 | 답변 |
|------|------|
| **YAML의 uni100이 왜 무시되나?** | Python 코드에서 `config['eval_args']`를 새로운 dict으로 완전히 교체했기 때문 |
| **sample_rate 0.1도 무시되나?** | 맞습니다. `config['valid_sample_rate'] = 1.0`으로 덮어씀 |
| **YAML 파일이 변경되나?** | 아니오. YAML은 그대로이고, 메모리의 config 객체만 변경됨 |
| **YAML을 Full로 바꾸면 안 되나?** | 가능하지만, 학습이 매우 느려집니다. 평가만 Full로 하는 것이 효율적 |

---

**작성일**: 2026-01-21
