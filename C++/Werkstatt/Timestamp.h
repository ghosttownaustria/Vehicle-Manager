#pragma once


#include <cstdint>
#include <chrono>
#include <string>


class Timestamp {
public:
  enum class TimestampFormat {
    DMY,
    DMY_HM,
    DMY_HMS,
    MDY,
    MDY_HM,
    MDY_HMS,
    YMD,
    YMD_HM,
    YMD_HMS,
    DAY,
    MONTH,
    YEAR,
    HOUR,
    MINUTE,
    SECOND
  };


  Timestamp();
  Timestamp(std::chrono::time_point<std::chrono::system_clock> tp);
  Timestamp(int64_t ms);
  Timestamp(std::string str);


  bool SetTimestamp(std::chrono::time_point<std::chrono::system_clock> tp);
  bool SetTimestamp(int64_t ms);
  bool SetTimestamp(std::string str);


  std::chrono::time_point<std::chrono::system_clock> GetTimestamp();
  int64_t GetTimestampMs();
  std::string GetTimestampString(TimestampFormat format = TimestampFormat::DMY_HMS, char dateSeparator = '.', char hourSeparator = ':');


protected:
  int64_t m_timestamp;


};
