# -*- coding: utf-8 -*-
from app.db.crud.student_crud import student_crud, StudentCRUD
from app.db.crud.match_result_crud import match_result_crud, MatchResultCRUD
from app.db.crud.report_crud import report_crud, ReportCRUD
from app.db.crud.chat_session_crud import chat_session_crud, ChatSessionCRUD
from app.db.crud.portrait_history_crud import portrait_history_crud, PortraitHistoryCRUD
from app.db.crud.job_trend_crud import job_trend_crud, JobTrendCRUD
from app.db.crud.job_real_crud import job_real_crud, JobRealCRUD
from app.db.crud.live_job_crud import LiveJobCRUD
from app.db.crud.user_memory_crud import UserMemoryCRUD

__all__ = [
    "student_crud", "StudentCRUD",
    "match_result_crud", "MatchResultCRUD",
    "report_crud", "ReportCRUD",
    "chat_session_crud", "ChatSessionCRUD",
    "portrait_history_crud", "PortraitHistoryCRUD",
    "job_trend_crud", "JobTrendCRUD",
    "job_real_crud", "JobRealCRUD",
    "LiveJobCRUD",
    "UserMemoryCRUD",
]
