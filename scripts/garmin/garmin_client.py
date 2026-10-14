import logging
import os
from enum import Enum, auto

from garminconnect import Garmin

logger = logging.getLogger(__name__)


def is_duplicate_activity(detailed_import_result):
  """Return whether Garmin's import response reports a duplicate activity."""
  if not isinstance(detailed_import_result, dict):
    return False

  failures = detailed_import_result.get("failures")
  if not isinstance(failures, list):
    return False

  for failure in failures:
    if not isinstance(failure, dict):
      continue
    messages = failure.get("messages")
    if not isinstance(messages, list):
      continue
    if any(
        isinstance(message, dict)
        and message.get("content") == "Duplicate Activity."
        for message in messages
    ):
      return True
  return False


class GarminClient:
  def __init__(self, email, password, auth_domain, newest_num):
    self.auth_domain = auth_domain
    self.email = email
    self.password = password
    self.newestNum = int(newest_num)
    self.api = None

  def _ensure_login(self):
    if self.api is None:
      is_cn = str(self.auth_domain).upper() == "CN"
      domain = "garmin.cn" if is_cn else "garmin.com"
      logger.info("Logging in to Garmin (%s)...", domain)
      self.api = Garmin(email=self.email, password=self.password, is_cn=is_cn)
      self.api.login()
    return self.api

  ## 获取运动
  def getActivities(self, start: int, limit: int):
    api = self._ensure_login()
    return api.get_activities(start, limit)

  ## 获取所有运动
  def getAllActivities(self):
    all_activities = []
    start = 0
    while True:
      activities = self.getActivities(start=start, limit=100)
      if activities and len(activities) > 0:
        all_activities.extend(activities)
      else:
        return all_activities
      start += 100

  ## 下载原始格式的运动
  def downloadFitActivity(self, activity_id):
    api = self._ensure_login()
    return api.download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)

  def upload_activity(self, activity_path: str):
    """Upload activity in fit format from file."""
    api = self._ensure_login()
    file_base_name = os.path.basename(activity_path)
    file_extension = file_base_name.split(".")[-1].upper()
    if file_extension not in ActivityUploadFormat.__members__:
      return "UPLOAD_EXCEPTION"

    status = "UPLOAD_EXCEPTION"
    try:
      result = api.upload_activity(activity_path)
      detailed_import_result = result.get("detailedImportResult") if isinstance(result, dict) else None
      upload_id = detailed_import_result.get("uploadId") if isinstance(detailed_import_result, dict) else None
      is_duplicate = upload_id is None or upload_id == ""
      if is_duplicate and detailed_import_result and is_duplicate_activity(detailed_import_result):
        status = "DUPLICATE_ACTIVITY"
      elif not is_duplicate:
        status = "SUCCESS"
      else:
        print(f"  -> upload result: {result}")
    except Exception as e:
      print(f"  -> exception: {e}")
      err_str = str(e)
      if "Duplicate" in err_str or "409" in err_str:
        status = "DUPLICATE_ACTIVITY"
      else:
        status = "UPLOAD_EXCEPTION"
    return status


class ActivityUploadFormat(Enum):
  FIT = auto()
  GPX = auto()
  TCX = auto()


class GarminNoLoginException(Exception):
  """Raised when Garmin login fails or rate limit is exceeded."""

  def __init__(self, status):
    super(GarminNoLoginException, self).__init__(status)
    self.status = status
