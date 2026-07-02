import hmac
import hashlib
import logging
from typing import Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

async def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """
    Verify the HMAC SHA-256 signature from GitHub.
    """
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set. Skipping signature verification.")
        return True # Depending on security posture, you might want to return False here in prod.
        
    if not signature_header:
        return False

    hash_object = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

async def process_pull_request_event(payload: dict[str, Any]):
    """
    Background task to process a pull request event.
    For now, it just logs. In future stairs, it will trigger the AI review pipeline.
    """
    from app.github.client import GitHubClient
    from app.github.service import GitHubService
    from app.services.pr_extraction import extract_pull_request

    action = payload.get("action")
    pr_number = payload.get("pull_request", {}).get("number")
    # repo_name is 'owner/repo', but we often need them separated
    repo_full_name = payload.get("repository", {}).get("full_name")
    
    if not repo_full_name or not pr_number:
        logger.error("Invalid pull request payload structure")
        return
        
    owner, repo = repo_full_name.split("/", 1)
    
    logger.info(f"Processing pull request event: action={action}, repo={repo_full_name}, pr={pr_number}")
    
    if action in ["opened", "synchronize", "reopened"]:
        logger.info(f"Extracting data for PR {pr_number} in {repo_full_name}...")
        
        # Instantiate GitHub client and service
        token = settings.GITHUB_TOKEN
        if not token:
            logger.warning("GITHUB_TOKEN is not set. API calls may fail due to rate limits or private repo access.")
            
        try:
            async with GitHubClient(token) as client:
                service = GitHubService(client)
                extracted_pr = await extract_pull_request(service, owner, repo, pr_number)
                
                logger.info(f"Extraction successful. Found {len(extracted_pr.files)} files to review.")
                # TODO: Trigger the LangGraph AI workflow here (Stair 7+) passing `extracted_pr`
                
        except Exception as e:
            logger.error(f"Failed to extract PR data: {e}", exc_info=True)
            
    else:
        logger.info(f"Ignoring pull request action: {action}")

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None)
):
    """
    Endpoint to receive GitHub webhooks.
    """
    logger.info(f"Received GitHub webhook event: {x_github_event}")
    
    # 1. Read raw body for signature verification
    payload_bytes = await request.body()
    
    # 2. Verify signature
    is_valid = await verify_signature(payload_bytes, x_hub_signature_256)
    if not is_valid:
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    # 3. Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Error parsing JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    # 4. Handle events
    if x_github_event == "ping":
        logger.info("Received ping event from GitHub. Webhook is working.")
        return {"status": "ok", "message": "Pong"}
        
    elif x_github_event == "pull_request":
        # Dispatch to background task to avoid blocking the webhook response
        background_tasks.add_task(process_pull_request_event, payload)
        return {"status": "accepted", "message": "Pull request event queued for processing"}
        
    else:
        logger.info(f"Ignored unhandled GitHub event: {x_github_event}")
        return {"status": "ignored", "message": "Unhandled event type"}
