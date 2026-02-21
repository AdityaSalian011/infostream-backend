import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import SessionLocal
from infoStreamDigest import InfoStreamDigest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_digest_job(target_time: str):
    """
    Run the digest job for a specific time slot.
    This function is called by the scheduler.
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting digest job for {target_time}")
        digest = InfoStreamDigest()
        result = digest.send_emails_batch(db, target_time=target_time)
        logger.info(f'Digest job for {target_time}: {result}')
    except Exception as e:
        logger.error(f"Error in digest job for {target_time}: {str(e)}")
    finally:
        db.close()

# Check for immediate emails every minute
def check_immediate_emails():
    """
    Check for and send immediate emails.
    Runs every minute.
    """
    db = SessionLocal()
    try:
        digest = InfoStreamDigest()
        result = digest.send_immediate_email(db)
        logger.info(f'Immediate digest job with result: {result}')
    except Exception as e:
        logger.error(f"Error checking immediate emails: {str(e)}")
    finally:
        db.close()

def start_scheduler():
    """
    Initialize and start the scheduler.
    Called when FastAPI app starts.
    """
    # Schedule digest jobs at specific times
    scheduler.add_job(
        lambda: run_digest_job('11:00'),
        CronTrigger(hour=11, minute=0),
        id='digest_11am',
        name='11:00 AM Digest',
        replace_existing=True
    )

    scheduler.add_job(
        lambda: run_digest_job('14:00'),
        CronTrigger(hour=14, minute=0),
        id='digest_2pm',
        name='2:00 PM Digest',
        replace_existing=True
    )

    scheduler.add_job(
        lambda: run_digest_job('17:00'),
        CronTrigger(hour=17, minute=0),
        id='digest_5pm',
        name='5:00 PM Digest',
        replace_existing=True
    )

    scheduler.add_job(
        lambda: run_digest_job('19:00'),
        CronTrigger(hour=19, minute=0),
        id='digest_7pm',
        name='7:00 PM Digest',
        replace_existing=True
    )

    scheduler.add_job(
        lambda: run_digest_job('21:00'),
        CronTrigger(hour=21, minute=0),
        id='digest_9pm',
        name='9:00 PM Digest',
        replace_existing=True
    )

    scheduler.add_job(
        lambda: run_digest_job('23:00'),
        CronTrigger(hour=23, minute=0),
        id='digest_11pm',
        name='11:00 PM Digest',
        replace_existing=True
    )

    # Check for immediate emails every minute
    scheduler.add_job(
        check_immediate_emails,
        'interval',
        minutes=1,
        id='check_immediate',
        name='Check Immediate Emails',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("✓ Scheduler started successfully")
    logger.info(f"✓ Scheduled jobs: {len(scheduler.get_jobs())}")

    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id})")

def stop_scheduler():
    """
    Stop the scheduler gracefully.
    Called when FastAPI app shuts down.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped gracefully")