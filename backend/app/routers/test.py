from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Game
router = APIRouter(
    prefix="/test",
    tags=["test"],
    responses={404: {"description": "Not found"}},
)

# ==============================================================================
# 1. "대조군" 실험 (기본 SELECT)
# Spring JPA: repository.findAll() 또는 JPQL
# Raw SQL: 직접 SQL 쿼리 문자열을 작성하여 실행합니다.
# ==============================================================================
@router.get("/raw-select")
def raw_select(db: Session = Depends(get_db)):
    """
    TODO: 아래 코드를 완성하여 'games' 테이블에서 5개의 게임을 가져오세요.
    
    [Keywords]
    - query 변수 생성: text("SQL Query") 
    - 실행: db.execute(query)
    """
    query = text("SELECT * FROM games LIMIT 5")
    result = db.execute(query)
    # 여기에 코드를 작성하세요
    
    return result

# ==============================================================================
# 2. "보안" 실험 (SQL Injection)
# Spring JPA: :param 문법을 사용하여 자동으로 바인딩 처리됨.
# Raw SQL: f-string(위험) vs Parameter Binding(안전) 직접 비교 필요.
# ==============================================================================
@router.get("/sql-injection")
def sql_injection(id_param: str, secure: bool = True, db: Session = Depends(get_db)):
    """
    TODO: secure=False일 때 SQL Injection이 발생하는 쿼리를 작성하고,
          secure=True일 때 파라미터 바인딩으로 막는 쿼리를 작성하세요.
          
    [Keywords]
    - Insecure (Bad): f"... {variable} ..."
    - Secure (Good): text("... WHERE id = :idx"), params={"idx": variable}
    """
    if not secure:
        # BAD PRACTICE: f-string 사용
        # id_param 자체가 쿼리 문자열의 일부로 해석되어 위험합니다.
        query_str = text(f"SELECT * FROM games WHERE game_id = {id_param}")
        result = db.execute(query_str)
        return result.all()
    else:
        # GOOD PRACTICE: Parameter Binding
        # id_param을 순수한 '값'으로만 취급하여 안전합니다.
        query_str = text("SELECT * FROM games WHERE game_id = :id")
        params = {"id": id_param}
        result = db.execute(query_str, params)
        return result.all()

# ==============================================================================
# 3. "사용성" 실험 (Mappings)
# Spring JPA: 엔티티 객체 리스트로 깔끔하게 반환됨.
# Raw SQL: 기본적으로 튜플 리스트((1, 'Overwatch'), ...) 반환. 딕셔너리로 변환 필요.
# ==============================================================================
@router.get("/mappings")
def mappings(db: Session = Depends(get_db)):
    """
    TODO: .mappings().all()을 사용하여 결과를 딕셔너리 리스트로 반환하세요.
    
    [Keywords]
    - db.execute(...).mappings().all()
    """
    # 여기에 코드를 작성하세요
    query = text("SELECT * FROM games LIMIT 5")
    # .mappings()를 호출해야 딕셔너리 형태로 변환됩니다.
    result = db.execute(query).mappings().all()
    
    return result

# ==============================================================================
# 4. "원자성" 실험 (트랜잭션)
# Spring JPA: @Transactional 어노테이션 하나로 해결.
# Raw SQL: 수동으로 커밋/롤백 시나리오를 이해해야 함.
# ==============================================================================
@router.post("/transaction")
def transaction_experiment(db: Session = Depends(get_db)):
    """
    TODO: 
    1. 첫 번째 INSERT 성공
    2. 두 번째 INSERT 실패 (의도적 에러)
    3. 전체 롤백 확인

    """
    try:
        # 1. 성공적인 INSERT (game_id와 title은 필수 컬럼입니다)
        # 999999 ID로 테스트용 데이터를 넣습니다.
        
        success_query = text("INSERT INTO games (game_id, title) VALUES (:id, :title)")
        db.execute(success_query, {"id": 999999, "title": "Transaction Test Game"})
        
        # 2. 강제 실패 (예: 존재하지 않는 컬럼 'ERROR_COL' 사용)
        error_query = text("INSERT INTO games (game_id, ERROR_COL) VALUES (999998, 'Fail')")
        db.execute(error_query)
        
        # 만약 여기까지 오면 커밋합니다 (하지만 위에서 에러가 나므로 실행 안 됨)
        db.commit()
    except Exception as e:
        # 에러가 발생하면 1번 INSERT도 취소(Rollback)되어야 합니다.
        db.rollback()
        return {"status": "rolled_back", "message": "Transaction Rolled Back! First insert was cancelled.", "error": str(e)}
        
    return {"status": "committed (should not happen in this experiment)"}

# ==============================================================================
# 5. "검증" 실험 (쿼리 확인)
# Spring JPA: application.yml에서 show-sql: true 설정.
# Raw SQL: 직접 로깅을 찍거나 echo=True 설정을 확인.
# ==============================================================================
@router.get("/debug")
def debug_query(db: Session = Depends(get_db)):
    """
    TODO: 실행할 쿼리를 미리 print()로 찍어보고 실행 결과를 확인하세요.
    
    [Keywords]
    - print(f"Query: {query}")
    - engine.echo = True (System level)
    """
    query_str = "SELECT count(*) FROM games"
    print(f"Executing Query: {query_str}")
    
    # 여기에 코드를 작성하세요
    
    return {"message": "Check your terminal console for the query log"}

# 6. "구현 실험"

@router.get("/games/{game_id}")
def read_game_orm(game_id: int, db: Session = Depends(get_db)):
    """
    TODO: SQLAchemy ORM을 사용해 game_id에 해당하는 게임 정보를 조회하세요
    없으면 404 에러를 변환해야 합니다.

        [Keywords]
    - db.query(Model)
    - .filter(Model.column == value)
    - .first()
      
    """

    # "Game 테이블에서, game_id가 입력받은 값과 같은 것을 찾아서, 첫 번째 놈을 가져와라"

    game = db.query(Game).filter(Game.game_id== game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
