#pragma once


#include <string>
#include <cstdint>


using UserId = uint64_t;

constexpr UserId kInvalidDefaultUserId = 0;


struct Address {};


enum class UserType {
  ADMIN,
  TECHNICIAN,
  CUSTOMER
};


class User {
public:


protected:
  UserId m_id;

  std::string m_visualUserNumber;

  std::string m_firstName;
  std::string m_lastName;

  std::string m_phoneNumber;

  Address m_address;
  UserType m_userType;

  std::string m_passwortHash;


};
