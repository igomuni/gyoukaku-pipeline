from pydantic import BaseModel, Field
from typing import Optional, List

class PipelineRunRequest(BaseModel):
    """パイプライン実行APIのリクエストボディモデル"""
    start_stage: int = Field(
        default=1, 
        description="パイプラインを開始するステージ番号 (1: CSV変換, 2: 正規化, 3: マスター構築, 4: 予算サマリー構築, 5: ZIPアーカイブ作成のみ)"
    )
    target_files: Optional[List[str]] = Field(
        default=None, 
        description="処理対象とするファイル名のリスト。指定しない場合はdownloadディレクトリ内の全ファイルが対象。"
    )

class JobCreationResponse(BaseModel):
    """パイプライン実行開始APIのレスポンスモデル"""
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    """パイプラインステータス確認APIのレスポンスモデル"""
    job_id: str
    status: str  # "pending", "in-progress", "completed", "failed", "cancelled"
    current_stage: Optional[str] = None
    message: Optional[str] = None
    results_url: Optional[str] = None
    error_message: Optional[str] = None
    cancel_requested: bool = False