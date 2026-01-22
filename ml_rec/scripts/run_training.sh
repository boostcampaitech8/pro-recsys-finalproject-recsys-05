#!/bin/bash

# GPU 훈련 스크립트 빠른 실행
# 사용: ./run_training.sh [옵션]
#   옵션:
#     (없음 또는 --foreground)  : 포그라운드 실행
#     --background              : 백그라운드 실행 (nohup)
#     --tmux                    : tmux 세션 생성 후 실행
#     --monitor                 : GPU 모니터링만 실행
#     --help                    : 이 도움말 출력

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/train_gpu_models.py"
LOG_FILE="$SCRIPT_DIR/training.log"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_python() {
    if ! command -v python &> /dev/null; then
        print_error "Python을 찾을 수 없습니다"
        exit 1
    fi
    print_success "Python 확인 완료: $(python --version)"
}

check_gpu() {
    if ! command -v nvidia-smi &> /dev/null; then
        print_warning "nvidia-smi를 찾을 수 없습니다 (GPU 드라이버 미설치 가능)"
        return 1
    fi

    if ! python -c "import torch; torch.cuda.is_available()" 2>/dev/null; then
        print_warning "PyTorch GPU 지원 불가능"
        return 1
    fi

    print_success "GPU 확인 완료"
    echo "$(nvidia-smi --query-gpu=name --format=csv,noheader)"
    return 0
}

run_foreground() {
    print_header "포그라운드 훈련 시작"
    print_info "실시간 로그 확인 가능 (Ctrl+C로 중단)"
    echo ""

    check_python
    check_gpu

    cd "$SCRIPT_DIR"
    python "$PYTHON_SCRIPT"
}

run_background() {
    print_header "백그라운드 훈련 시작"
    print_info "로그: $LOG_FILE"
    echo ""

    check_python
    check_gpu

    cd "$SCRIPT_DIR"

    # 이미 실행 중인 프로세스 확인
    if pgrep -f "train_gpu_models.py" > /dev/null 2>&1; then
        print_warning "훈련이 이미 실행 중입니다"
        ps aux | grep train_gpu_models.py | grep -v grep
        return 1
    fi

    # 백그라운드 실행
    nohup python "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1 &
    local PID=$!

    print_success "훈련 시작 (PID: $PID)"
    print_info "로그 추적: tail -f $LOG_FILE"
    print_info "진행 상황: watch -n 1 nvidia-smi"
    print_info "프로세스 종료: kill $PID"

    sleep 2
    echo ""
    tail -20 "$LOG_FILE"
}

run_tmux() {
    print_header "tmux 세션 생성 및 훈련 시작"
    echo ""

    check_python
    check_gpu

    local SESSION_NAME="training"

    # 이미 존재하는 세션 확인
    if tmux list-sessions 2>/dev/null | grep -q "^$SESSION_NAME"; then
        print_warning "이미 '$SESSION_NAME' 세션이 존재합니다"
        tmux list-sessions | grep "$SESSION_NAME"
        print_info "세션 연결: tmux attach -t $SESSION_NAME"
        print_info "세션 종료: tmux kill-session -t $SESSION_NAME"
        return 1
    fi

    # 새 세션 생성
    tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR"
    print_success "tmux 세션 생성: $SESSION_NAME"

    # 훈련 시작
    tmux send-keys -t "$SESSION_NAME" "python $PYTHON_SCRIPT" Enter
    print_success "훈련 시작"

    echo ""
    print_info "세션 연결: tmux attach -t $SESSION_NAME"
    print_info "세션 분리: Ctrl+B, D"
    print_info "세션 목록: tmux list-sessions"
    print_info "세션 종료: tmux kill-session -t $SESSION_NAME"
}

run_monitor() {
    print_header "GPU 모니터링"
    print_info "1초마다 업데이트 (Ctrl+C로 종료)"
    echo ""

    if ! command -v watch &> /dev/null; then
        print_warning "watch 명령을 찾을 수 없습니다. nvidia-smi 직접 실행:"
        nvidia-smi
    else
        watch -n 1 nvidia-smi
    fi
}

show_help() {
    cat << 'EOF'
GPU 훈련 스크립트 빠른 실행

사용법:
    ./run_training.sh [옵션]

옵션:
    (없음) 또는 --foreground   : 포그라운드 실행 (권장)
    --background              : 백그라운드 실행 (nohup)
    --tmux                    : tmux 세션에서 실행
    --monitor                 : GPU 모니터링만 실행
    --help, -h                : 이 도움말 출력

예시:
    # 포그라운드 실행
    ./run_training.sh

    # 백그라운드 실행
    ./run_training.sh --background
    tail -f training.log

    # tmux 세션 사용
    ./run_training.sh --tmux
    tmux attach -t training

    # 모니터링
    ./run_training.sh --monitor

주의:
    - 포그라운드: 터미널을 닫으면 훈련이 중단됩니다
    - 백그라운드: 터미널을 닫아도 계속 실행됩니다
    - tmux: 고급 사용자용, attach/detach 가능합니다

더 자세한 정보:
    cat TRAINING_GUIDE.md

EOF
}

# 메인
main() {
    case "${1:-}" in
        --foreground|"")
            run_foreground
            ;;
        --background)
            run_background
            ;;
        --tmux)
            run_tmux
            ;;
        --monitor)
            run_monitor
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
}

# 실행
main "$@"
