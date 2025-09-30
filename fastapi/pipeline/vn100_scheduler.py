"""
VN100 Weekly Scheduler

Module để schedule cập nhật VN100 hàng tuần tự động với:
- Cron job scheduling
- Error handling và retry
- Logging và monitoring
- Email notifications
- Health checks
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Import VN100 updater
from fastapi.pipeline.vn100_updater import run_vn100_weekly_update

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/vn100_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VN100Scheduler:
    """
    VN100 Weekly Scheduler
    
    Scheduler để chạy cập nhật VN100 hàng tuần với:
    - Automatic scheduling (every Monday at 6 AM)
    - Error handling và retry mechanism
    - Email notifications
    - Health monitoring
    - Logging và reporting
    """
    
    def __init__(self, config_file: str = "config/scheduler_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[Dict] = None
        self.error_count = 0
        self.max_retries = 3
        
        # Setup log directory
        Path("logs").mkdir(exist_ok=True)
        
    def _load_config(self) -> Dict:
        """Load scheduler configuration"""
        default_config = {
            "schedule_time": "06:00",  # 6 AM
            "schedule_day": "monday",  # Every Monday
            "timezone": "Asia/Ho_Chi_Minh",
            "email_notifications": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "recipients": []
            },
            "retry_config": {
                "max_retries": 3,
                "retry_delay": 300,  # 5 minutes
                "backoff_factor": 2
            },
            "health_check": {
                "enabled": True,
                "check_interval": 3600,  # 1 hour
                "max_failures": 5
            }
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Create default config file
                Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default config file: {self.config_file}")
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return default_config
    
    async def _run_update_with_retry(self) -> Dict:
        """
        Chạy cập nhật VN100 với retry mechanism
        
        Returns:
            Update result dictionary
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"🚀 Starting VN100 update (attempt {retry_count + 1}/{self.max_retries})")
                
                result = await run_vn100_weekly_update()
                
                if result.get('success', False):
                    logger.info("✅ VN100 update completed successfully")
                    self.error_count = 0
                    return result
                else:
                    error_msg = result.get('error_message', 'Unknown error')
                    logger.warning(f"⚠️ VN100 update failed: {error_msg}")
                    last_error = error_msg
                    
            except Exception as e:
                error_msg = f"Exception during update: {str(e)}"
                logger.error(f"❌ {error_msg}")
                last_error = error_msg
            
            retry_count += 1
            
            if retry_count < self.max_retries:
                delay = self.config['retry_config']['retry_delay'] * (self.config['retry_config']['backoff_factor'] ** (retry_count - 1))
                logger.info(f"⏳ Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        # All retries failed
        self.error_count += 1
        logger.error(f"❌ VN100 update failed after {self.max_retries} attempts")
        
        return {
            'success': False,
            'error_message': f"Failed after {self.max_retries} attempts. Last error: {last_error}",
            'retry_count': retry_count,
            'timestamp': datetime.now()
        }
    
    async def _send_notification(self, result: Dict) -> None:
        """
        Gửi email notification về kết quả cập nhật
        
        Args:
            result: Update result dictionary
        """
        if not self.config['email_notifications']['enabled']:
            return
        
        try:
            email_config = self.config['email_notifications']
            
            # Create email content
            subject = f"VN100 Weekly Update - {'Success' if result.get('success') else 'Failed'}"
            
            if result.get('success'):
                body = f"""
VN100 Weekly Update Completed Successfully!

📅 Week: {result.get('week_start', 'N/A')} to {result.get('week_end', 'N/A')}
⏱️ Duration: {result.get('update_duration', 0):.2f} seconds
📊 Results:
  - Scraped: {result.get('total_scraped', 0)}
  - Verified: {result.get('total_verified', 0)}
  - Tested: {result.get('total_tested', 0)}
  - Final symbols: {result.get('final_symbols', 0)}
  - New symbols: {result.get('new_symbols', 0)}
  - Active symbols: {result.get('active_symbols', 0)}
  - Inactive symbols: {result.get('inactive_symbols', 0)}
  - Success rate: {result.get('success_rate', 0):.1%}

🆕 New symbols: {', '.join(result.get('new_symbols_list', []))}
❌ Inactive symbols: {', '.join(result.get('inactive_symbols_list', []))}

Timestamp: {result.get('timestamp', datetime.now())}
                """
            else:
                body = f"""
VN100 Weekly Update Failed!

❌ Error: {result.get('error_message', 'Unknown error')}
🔄 Retry count: {result.get('retry_count', 0)}
⏰ Timestamp: {result.get('timestamp', datetime.now())}

Please check the logs for more details.
                """
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['recipients'], text)
            server.quit()
            
            logger.info("📧 Email notification sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to send email notification: {str(e)}")
    
    async def _health_check(self) -> bool:
        """
        Kiểm tra health của scheduler
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if last run was too long ago
            if self.last_run:
                time_since_last_run = datetime.now() - self.last_run
                if time_since_last_run > timedelta(days=8):  # More than a week
                    logger.warning("⚠️ Health check failed: Last run was too long ago")
                    return False
            
            # Check error count
            if self.error_count > self.config['health_check']['max_failures']:
                logger.warning(f"⚠️ Health check failed: Too many errors ({self.error_count})")
                return False
            
            logger.info("✅ Health check passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Health check error: {str(e)}")
            return False
    
    async def _scheduled_update(self) -> None:
        """Scheduled update function"""
        try:
            logger.info("🕐 Scheduled VN100 update triggered")
            
            # Run update with retry
            result = await self._run_update_with_retry()
            
            # Store result
            self.last_result = result
            self.last_run = datetime.now()
            
            # Send notification
            await self._send_notification(result)
            
            # Log result
            if result.get('success'):
                logger.info(f"🎉 Scheduled update completed: {result.get('final_symbols', 0)} symbols")
            else:
                logger.error(f"❌ Scheduled update failed: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error in scheduled update: {str(e)}")
            self.error_count += 1
    
    def start_scheduler(self) -> None:
        """Start the scheduler"""
        if self.is_running:
            logger.warning("⚠️ Scheduler is already running")
            return
        
        logger.info("🚀 Starting VN100 Weekly Scheduler...")
        
        # Setup schedule
        schedule_time = self.config['schedule_time']
        schedule_day = self.config['schedule_day']
        
        # Schedule the update
        if schedule_day.lower() == 'monday':
            schedule.every().monday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'tuesday':
            schedule.every().tuesday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'wednesday':
            schedule.every().wednesday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'thursday':
            schedule.every().thursday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'friday':
            schedule.every().friday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'saturday':
            schedule.every().saturday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        elif schedule_day.lower() == 'sunday':
            schedule.every().sunday.at(schedule_time).do(lambda: asyncio.create_task(self._scheduled_update()))
        else:
            logger.error(f"❌ Invalid schedule day: {schedule_day}")
            return
        
        # Schedule health check
        if self.config['health_check']['enabled']:
            check_interval = self.config['health_check']['check_interval']
            schedule.every(check_interval).seconds.do(lambda: asyncio.create_task(self._health_check()))
        
        self.is_running = True
        logger.info(f"✅ Scheduler started - Updates scheduled for {schedule_day} at {schedule_time}")
        
        # Run scheduler loop
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")
        except Exception as e:
            logger.error(f"❌ Scheduler error: {str(e)}")
        finally:
            self.is_running = False
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler"""
        logger.info("🛑 Stopping VN100 Weekly Scheduler...")
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            'is_running': self.is_running,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'error_count': self.error_count,
            'last_result': self.last_result,
            'config': self.config,
            'next_run': schedule.next_run().isoformat() if schedule.jobs else None
        }
    
    async def run_manual_update(self) -> Dict:
        """
        Chạy cập nhật thủ công
        
        Returns:
            Update result
        """
        logger.info("🔧 Running manual VN100 update...")
        result = await self._run_update_with_retry()
        self.last_result = result
        self.last_run = datetime.now()
        return result

def create_scheduler_config(
    schedule_time: str = "06:00",
    schedule_day: str = "monday",
    email_enabled: bool = False,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    username: str = "",
    password: str = "",
    recipients: List[str] = None
) -> Dict:
    """
    Tạo config file cho scheduler
    
    Args:
        schedule_time: Time to run (HH:MM format)
        schedule_day: Day of week
        email_enabled: Enable email notifications
        smtp_server: SMTP server
        smtp_port: SMTP port
        username: Email username
        password: Email password
        recipients: List of email recipients
        
    Returns:
        Config dictionary
    """
    if recipients is None:
        recipients = []
    
    config = {
        "schedule_time": schedule_time,
        "schedule_day": schedule_day,
        "timezone": "Asia/Ho_Chi_Minh",
        "email_notifications": {
            "enabled": email_enabled,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "recipients": recipients
        },
        "retry_config": {
            "max_retries": 3,
            "retry_delay": 300,
            "backoff_factor": 2
        },
        "health_check": {
            "enabled": True,
            "check_interval": 3600,
            "max_failures": 5
        }
    }
    
    return config

if __name__ == "__main__":
    async def main():
        """Test function"""
        print(f"\n{'='*60}")
        print(f"VN100 Weekly Scheduler Test")
        print(f"{'='*60}")
        
        # Create test config
        config = create_scheduler_config(
            schedule_time="06:00",
            schedule_day="monday",
            email_enabled=False
        )
        
        # Save config
        Path("config").mkdir(exist_ok=True)
        with open("config/scheduler_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        # Create scheduler
        scheduler = VN100Scheduler()
        
        # Test manual update
        print("\n🔧 Testing manual update...")
        result = await scheduler.run_manual_update()
        
        if result.get('success'):
            print(f"✅ Manual update successful: {result.get('final_symbols', 0)} symbols")
        else:
            print(f"❌ Manual update failed: {result.get('error_message', 'Unknown error')}")
        
        # Show status
        print(f"\n📊 Scheduler Status:")
        status = scheduler.get_status()
        print(f"  Running: {status['is_running']}")
        print(f"  Last run: {status['last_run']}")
        print(f"  Error count: {status['error_count']}")
        print(f"  Next run: {status['next_run']}")
        
        print(f"\n{'='*60}")
        print("To start the scheduler, run: scheduler.start_scheduler()")
        print("To stop the scheduler, run: scheduler.stop_scheduler()")
        print(f"{'='*60}")
    
    asyncio.run(main())
