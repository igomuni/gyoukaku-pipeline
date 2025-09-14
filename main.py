import os
from typing import List
from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from models.api_models import (
    JobCreationResponse, JobStatusResponse, PipelineRunRequest
)
from pipeline.manager import (
    create_new_job, get_job_status, run_pipeline_async, get_all_jobs, 
    request_job_cancellation
)
from config import PROCESSED_DIR, DOWNLOAD_DIR, RAW_DIR, NORMALIZED_DIR

app = FastAPI(
    title="行政事業レビューシート データ処理パイプライン API",
    description="Excel/ZIP形式の元データを処理・正規化するためのバックエンドサービス",
    version="1.1.0",
)

@app.post("/api/pipeline/run", 
            response_model=JobCreationResponse, 
            status_code=status.HTTP_202_ACCEPTED,
            summary="データ処理パイプラインを開始")
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks
):
    """
    データ処理パイプラインを非同期のバックグラウンドタスクとして開始します。

    - **start_stage**: 開始ステージを指定 (1-4)。途中から再開する場合に使用します。
    - **target_files**: 処理対象のファイル名をリストで指定。指定しない場合は全ファイルが対象です。
    """
    job_id = create_new_job()
    background_tasks.add_task(run_pipeline_async, job_id, request.start_stage, request.target_files)
    return {"job_id": job_id, "message": "パイプラインの実行を受け付けました。"}

@app.get("/api/pipeline/jobs",
           response_model=List[JobStatusResponse],
           summary="全ジョブの一覧を取得")
async def list_all_jobs():
    """
    これまでに実行された、または実行中の全てのジョブのリストを返します。
    """
    return get_all_jobs()

@app.get("/api/pipeline/status/{job_id}", 
           response_model=JobStatusResponse,
           summary="パイプラインの実行状況を確認")
async def get_pipeline_status(job_id: str):
    """
    指定された `job_id` のパイプライン実行状況（ステータス、進捗など）を返します。
    """
    status_info = get_job_status(job_id)
    if not status_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job ID '{job_id}' not found.")
    return status_info

@app.post("/api/pipeline/cancel/{job_id}",
            summary="実行中のパイプラインをキャンセル")
async def cancel_pipeline_job(job_id: str):
    """
    実行中のパイプラインのキャンセルを要求します。
    即時停止ではなく、現在のファイル処理が完了した後に安全に停止します。
    """
    if not get_job_status(job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job ID '{job_id}' not found.")
    
    success = request_job_cancellation(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Job {job_id} is not in a cancellable state (must be 'in-progress')."
        )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": f"Cancellation request for job {job_id} accepted."}
    )

@app.get("/api/results/{filename}",
           summary="処理済みデータをダウンロード")
async def download_results(filename: str):
    """
    処理が完了した成果物（ZIPファイルなど）をダウンロードします。
    ファイル名は `/api/pipeline/status/{job_id}` エンドポイントの完了時レスポンスに含まれる
    `results_url` から取得してください。
    """
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    file_path = PROCESSED_DIR / filename
    
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        
    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=filename
    )

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にディレクトリを作成する"""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "データ処理パイプラインAPIへようこそ。APIドキュメントは /docs を参照してください。"}