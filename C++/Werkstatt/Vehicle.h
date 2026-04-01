#pragma once


#include <string>
#include <cstdint>


#include "User.h"


using VehicleId = uint64_t;


struct LicensePlate {
  std::string m_country;
  std::string m_distinguishingMark;
  std::string m_identificationNumber;
};


enum class FuelType {
  GASOLINE,
  DIESEL,
  ELECTRIC,
  LPG_CNG,
  BIO_FUEL,
  HYDROGEN,
  SPECIAL
};


class Vehicle {
public:


protected:
  VehicleId m_id;
  UserId m_userId;


  std::string m_brand;
  std::string m_model;
  std::string m_vin;

  LicensePlate m_licensePlate;
  std::string m_engineType;
  FuelType m_fuelType;



};
