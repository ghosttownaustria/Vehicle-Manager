#pragma once


#include <string>
#include <cstdint>


#include "Vehicle.h"


using ContractId = uint64_t;

constexpr ContractId kInvalidDefaultContractId = 0;


class Contract {
public:


private:
  ContractId m_id;
  VehicleId m_vehicleId;

  std::string m_titel;
  std::string m_description;


};
