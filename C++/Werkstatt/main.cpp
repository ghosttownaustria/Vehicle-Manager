#include <iostream>


#include "Register.h"
#include "Timestamp.h"


int main() {

  Timestamp timestamp;

  timestamp.SetTimestamp("2026-04-07 16:15:26");
  std::cout << timestamp.GetTimestampString() << std::endl;


  TimeRegister test;
  test.m_start = Timestamp("2026-04-07 16:15:26");
  test.m_stop = Timestamp("2026-04-07 16:15:26");
  test.m_userId = kInvalidDefaultUserId;

  std::cout << sizeof(test) << std::endl;

  return 0;
}
