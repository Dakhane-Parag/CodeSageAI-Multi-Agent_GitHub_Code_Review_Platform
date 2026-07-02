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
    Extracts the PR data and invokes the LangGraph review workflow.
    """
    from app.github.client import GitHubClient
    from app.github.service import GitHubService
    from app.services.pr_extraction import extract_pull_request
    from app.workflows.review_workflow import review_workflow

    action = payload.get("action")
    pr_number = payload.get("pull_request", {}).get("number")
    repo_full_name = payload.get("repository", {}).get("full_name")
    
    if not repo_full_name or not pr_number:
        logger.error("Invalid pull request payload structure")
        return
        
    owner, repo = repo_full_name.split("/", 1)
    
    logger.info(f"Processing pull request event: action={action}, repo={repo_full_name}, pr={pr_number}")
    
    if action in ["opened", "synchronize", "reopened"]:
        logger.info(f"Extracting data for PR #{pr_number} in {repo_full_name}...")
        
        token = settings.GITHUB_TOKEN
        if not token:
            logger.warning("GITHUB_TOKEN is not set. API calls may fail.")
            
        try:
            async with GitHubClient(token) as client:
                service = GitHubService(client)

                # Step 1: Extract and classify the PR
                extracted_pr = await extract_pull_request(service, owner, repo, pr_number)
                logger.info(f"Extraction successful. Found {len(extracted_pr.files)} files to review.")

                # Step 2: Build the initial workflow state from the extracted PR
                initial_state = {
                    "owner": owner,
                    "repo": repo,
                    "pr_number": pr_number,
                    "pr_title": extracted_pr.title,
                    "pr_author": extracted_pr.author,
                    "pr_files": [f.model_dump() for f in extracted_pr.files],
                    "security_findings": [],
                    "performance_findings": [],
                    "quality_findings": [],
                    "testing_findings": [],
                    "aggregated_review": None,
                    "errors": [],
                }

                # Step 3: Invoke the LangGraph review workflow
                logger.info(f"Invoking LangGraph review workflow for PR #{pr_number}...")
                final_state = await review_workflow.ainvoke(initial_state)
                logger.info(f"Review workflow completed for PR #{pr_number}.")
                
                # Step 4: Persist the AI review to MongoDB
                try:
                    from app.db.session import get_database
                    from app.db.repositories.ai_reviews import AiReviewRepository
                    from app.models.ai_review import AiReviewInDB

                    db = get_database()
                    repo_db = AiReviewRepository(db)
                    
                    # Combine findings for the model
                    all_findings = (
                        final_state.get("security_findings", []) +
                        final_state.get("performance_findings", []) +
                        final_state.get("quality_findings", []) +
                        final_state.get("testing_findings", [])
                    )

                    review_doc = AiReviewInDB(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        pr_title=final_state.get("pr_title", ""),
                        total_findings=len(all_findings),
                        findings=all_findings,
                        markdown_report=final_state.get("aggregated_review", "")
                    )
                    
                    await repo_db.create(review_doc)
                    logger.info(f"Successfully saved AI review for PR #{pr_number} to MongoDB.")
                except Exception as db_err:
                    logger.error(f"Failed to save AI review to MongoDB: {db_err}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Failed to process PR #{pr_number}: {e}", exc_info=True)
            
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
