import logging
from typing import Dict, Any
from data_models.schemas import AnalysisTask
from core.config_loader import get_service_urls
# We will import connectors dynamically in create_task to avoid circular imports.

###############################################################################
# File: core/orchestrator.py
#
# Purpose:
# The AnalysisOrchestrator decides which external connector to call based on the 
# type of task (message, link, file, app). It uses the data in AnalysisTask to 
# determine the correct external service and request an analysis. The returned 
# reference (like a task_id from external service) is what we store as the 
# resulting "task_id" from orchestrator's perspective.
#
# Design & Philosophy:
# - Orchestrator acts as a routing logic: given a task_data, it calls the 
#   corresponding connector function.
# - Connectors are external modules that perform HTTP calls to services (mocked 
#   in tests, real in production).
# - If an unknown task type is encountered, raise ValueError for fail-fast.
#
# Maintainability:
# - If we add new task types (e.g., "image"), just update create_task logic.
# - If connectors or services change, update references here.
#
# Testing:
# - We tested in test_orchestrator.py with mocks.
#
# Steps:
# 1) Identify task type from AnalysisTask
# 2) Call correct connector and return the reference it provides
#
###############################################################################

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    def __init__(self):
        """
        Initialize orchestrator.
        We might load service URLs from config if needed. Though connectors 
        each load from ENV via config_loader in their own module.
        For now, orchestrator doesn't need direct URLs because connectors handle that.
        """
        # Optional: store service_urls if we want to verify or 
        # rely on them. Not strictly needed if connectors handle their own env loading.
        self.service_urls = get_service_urls()
        logger.info("AnalysisOrchestrator initialized with service URLs.")

    def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Given an AnalysisTask-like dict (type, content, timestamp),
        decide which connector to call:
        - type == "message": call message_service_connector.analyze_message(content)
        - type == "link": call link_service_connector.analyze_link(url, visual_verify)
          If visual_verify is not in task_data, default to False.
        - type == "file": call file_service_connector.analyze_file(file_ref)
        - type == "app": call app_service_connector.analyze_app(app_ref)
        
        Returns:
            str: A reference/task_id returned by the connector.
        
        Raises:
            ValueError: if unknown task type.
        """

        # Validate task_data structure. We assume AnalysisTask format.
        # We can rely on previous validation if performed by endpoints.
        task_type = task_data.get("type")
        content = task_data.get("content")

        if not task_type or not content:
            logger.error("task_data missing type or content fields.")
            raise ValueError("task_data must have 'type' and 'content'.")

        # Import connectors here to avoid circular imports and only when needed.
        # Typically, connectors are lightweight so this is fine.
        from connectors.message_service_connector import analyze_message
        from connectors.link_service_connector import analyze_link
        from connectors.file_service_connector import analyze_file
        from connectors.app_service_connector import analyze_app

        if task_type == "message":
            # Message tasks
            logger.info(f"Creating message task for content={content}.")
            return analyze_message(content)

        elif task_type == "link":
            # Link tasks may also have a "visual_verify" field if specified by requesters.
            # If not provided, default False.
            visual_verify = task_data.get("visual_verify", False)
            logger.info(f"Creating link task for url={content}, visual_verify={visual_verify}.")
            return analyze_link(content, visual_verify)

        elif task_type == "file":
            # File tasks: content is file_ref
            logger.info(f"Creating file task for file_ref={content}.")
            return analyze_file(content)

        elif task_type == "app":
            # App tasks: content is app_ref
            logger.info(f"Creating app task for app_ref={content}.")
            return analyze_app(content)

        else:
            logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")


###############################################################################
# Future Extensions:
# - If we need to handle more types, add cases here.
# - If advanced routing logic needed (e.g., different connectors per environment),
#   implement conditions or load from config.
#
# Not the last file:
# We will still implement api routes, admin_ui/gradio_dashboard.py, and connectors/*.
# We'll notify after the final file is provided.
###############################################################################
