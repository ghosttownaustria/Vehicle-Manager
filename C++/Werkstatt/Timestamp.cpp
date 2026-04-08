#include "Timestamp.h"


#include <sstream>
#include <iomanip>
#include <ctime>


Timestamp::Timestamp() : m_timestamp(0) {}


Timestamp::Timestamp(std::chrono::time_point<std::chrono::system_clock> tp) {
  SetTimestamp(tp);
}


Timestamp::Timestamp(int64_t ms) {
  SetTimestamp(ms);
}


Timestamp::Timestamp(std::string str) {
  SetTimestamp(str);
}


bool Timestamp::SetTimestamp(std::chrono::time_point<std::chrono::system_clock> tp) {
  m_timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
    tp.time_since_epoch()
  ).count();
  return true;
}


bool Timestamp::SetTimestamp(int64_t ms) {
  m_timestamp = ms;
  return true;
}


bool Timestamp::SetTimestamp(std::string str) {
  std::tm tm = {};
  std::istringstream ss(str);

  // Expected format: YYYY-MM-DD HH:MM:SS
  ss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S");

  if (ss.fail()) {
    return false;
  }

  std::time_t time = std::mktime(&tm);
  if (time == -1) {
    return false;
  }

  m_timestamp = static_cast<int64_t>(time) * 1000;
  return true;
}


std::chrono::time_point<std::chrono::system_clock> Timestamp::GetTimestamp() {
  return std::chrono::time_point<std::chrono::system_clock>(
    std::chrono::milliseconds(m_timestamp)
  );
}


int64_t Timestamp::GetTimestampMs() {
  return m_timestamp;
}


std::string Timestamp::GetTimestampString(TimestampFormat format, char dateSeparator, char hourSeparator) {
  std::time_t time = m_timestamp / 1000;

  std::tm tm{};
#if defined(_WIN32)
  localtime_s(&tm, &time);
#else
  localtime_r(&time, &tm);
#endif

  std::ostringstream ss;

  auto twoDigit = [](int value) {
    std::ostringstream s;
    s << std::setw(2) << std::setfill('0') << value;
    return s.str();
    };

  switch (format) {
  case TimestampFormat::DMY:
    ss << twoDigit(tm.tm_mday) << dateSeparator
      << twoDigit(tm.tm_mon + 1) << dateSeparator
      << (tm.tm_year + 1900);
    break;

  case TimestampFormat::DMY_HM:
    ss << GetTimestampString(TimestampFormat::DMY, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min);
    break;

  case TimestampFormat::DMY_HMS:
    ss << GetTimestampString(TimestampFormat::DMY, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min) << hourSeparator
      << twoDigit(tm.tm_sec);
    break;

  case TimestampFormat::MDY:
    ss << twoDigit(tm.tm_mon + 1) << dateSeparator
      << twoDigit(tm.tm_mday) << dateSeparator
      << (tm.tm_year + 1900);
    break;

  case TimestampFormat::MDY_HM:
    ss << GetTimestampString(TimestampFormat::MDY, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min);
    break;

  case TimestampFormat::MDY_HMS:
    ss << GetTimestampString(TimestampFormat::MDY, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min) << hourSeparator
      << twoDigit(tm.tm_sec);
    break;

  case TimestampFormat::YMD:
    ss << (tm.tm_year + 1900) << dateSeparator
      << twoDigit(tm.tm_mon + 1) << dateSeparator
      << twoDigit(tm.tm_mday);
    break;

  case TimestampFormat::YMD_HM:
    ss << GetTimestampString(TimestampFormat::YMD, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min);
    break;

  case TimestampFormat::YMD_HMS:
    ss << GetTimestampString(TimestampFormat::YMD, dateSeparator)
      << " "
      << twoDigit(tm.tm_hour) << hourSeparator
      << twoDigit(tm.tm_min) << hourSeparator
      << twoDigit(tm.tm_sec);
    break;

  case TimestampFormat::DAY:
    ss << tm.tm_mday;
    break;

  case TimestampFormat::MONTH:
    ss << (tm.tm_mon + 1);
    break;

  case TimestampFormat::YEAR:
    ss << (tm.tm_year + 1900);
    break;

  case TimestampFormat::HOUR:
    ss << tm.tm_hour;
    break;

  case TimestampFormat::MINUTE:
    ss << tm.tm_min;
    break;

  case TimestampFormat::SECOND:
    ss << tm.tm_sec;
    break;
  }

  return ss.str();
}
