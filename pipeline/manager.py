import uuid
import logging
import traceback
import zipfile
from typing import Dict, Any, Optional, List
from threading import Lock

from config import PROCESSED_DIR
from pipeline.stages import run_stage_01_convert, run_stage_02_normalize, run_stage_03_build_masters

# --- グローバルな状態管理 ---
# インメモリでジョブの状態を管理
jobs: Dict[str, Dict[str, Any]] = {}
# パイプラインの同時実行を防ぐためのロック
PIPELINE_LOCK = Lock()

class JobCancelledError(Exception):
    """ジョブキャンセルのためのカスタム例外"""
    pass

def check_for_cancellation(job_id: str):
    """ジョブのキャンセル要求をチェックし、要求があれば例外を送出する"""
    if jobs.get(job_id, {}).get("cancel_requested", False):
        raise JobCancelledError(f"Job {job_id} was cancelled by user.")

def create_new_job() -> str:
    """新しいジョブを作成し、ジョブIDを返す"""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "current_stage": None,
        "message": "パイプラインの開始を待っています...",
        "results_url": None,
        "error_message": None,
        "cancel_requested": False,
    }
    return job_id

def get_all_jobs() -> List[Dict[str, Any]]:
    """全ジョブのステータスリストを返す"""
    return sorted(list(jobs.values()), key=lambda j: j.get('start_time', 0), reverse=True)

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """指定されたジョブIDのステータスを返す"""
    return jobs.get(job_id)

def request_job_cancellation(job_id: str) -> bool:
    """指定されたジョブのキャンセルを要求する"""
    if job_id in jobs and jobs[job_id]["status"] == "in-progress":
        jobs[job_id]["cancel_requested"] = True
        jobs[job_id]["message"] = "キャンセル要求を受け付けました。現在の処理が完了次第停止します。"
        logging.warning(f"Cancellation requested for job {job_id}.")
        return True
    return False

def run_pipeline_async(job_id: str, start_stage: int, target_files: Optional[List[str]]):
    """
    データ処理パイプライン全体を非同期で実行する
    """
    if not PIPELINE_LOCK.acquire(blocking=False):
        logging.warning(f"Pipeline execution denied for job {job_id}: another pipeline is already running.")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error_message"] = "他のパイプラインが実行中のため、開始できませんでした。"
        return

    try:
        import time
        jobs[job_id]["start_time"] = time.time()
        
        def update_status(current_stage: str = None, message: str = None):
            check_for_cancellation(job_id)
            if current_stage:
                jobs[job_id]["current_stage"] = current_stage
            if message:
                jobs[job_id]["message"] = message
            logging.info(f"[Job {job_id}] {jobs[job_id]['current_stage']}: {jobs[job_id]['message']}")

        logging.info(f"Starting pipeline for job_id: {job_id}")
        jobs[job_id]["status"] = "in-progress"

        if start_stage <= 1:
            run_stage_01_convert(update_status, job_id, target_files)
        
        if start_stage <= 2:
            run_stage_02_normalize(update_status, job_id)
        
        if start_stage <= 3:
            run_stage_03_build_masters(update_status, job_id)
        
        check_for_cancellation(job_id)
        update_status(current_stage="ステージ4: ZIPアーカイブ作成", message="成果物をZIPアーカイブにまとめています...")
        
        zip_filename = f"processed_data_{job_id}.zip"
        zip_filepath = PROCESSED_DIR / zip_filename

        files_to_zip = list(PROCESSED_DIR.glob('*.csv'))
        
        if not files_to_zip:
             logging.warning(f"No CSV files found in {PROCESSED_DIR} to zip.")
        else:
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in files_to_zip:
                    zf.write(file, arcname=file.name)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "パイプラインは正常に完了しました。"
        jobs[job_id]["current_stage"] = "完了"
        jobs[job_id]["results_url"] = f"/api/results/{zip_filename}"
        logging.info(f"Pipeline for job_id: {job_id} completed successfully.")

    except JobCancelledError as e:
        logging.warning(str(e))
        jobs[job_id]["status"] = "cancelled"
        jobs[job_id]["message"] = "ユーザーのリクエストによりパイプラインはキャンセルされました。"
        jobs[job_id]["current_stage"] = "キャンセル済み"

    except Exception as e:
        tb_str = traceback.format_exc()
        logging.error(f"Pipeline for job_id: {job_id} failed. Error: {e}\n{tb_str}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error_message"] = f"ステージ '{jobs[job_id].get('current_stage', '不明')}' でエラーが発生しました: {e}"
        jobs[job_id]["message"] = "パイプラインの実行中にエラーが発生しました。"
    
    finally:
        PIPELINE_LOCK.release()
        logging.info(f"Pipeline lock released for job {job_id}.")