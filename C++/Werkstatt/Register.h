#pragma once


#include <string>
#include <cstdint>


#include <chrono>
#include <vector>


#include "User.h"
#include "Vehicle.h"
#include "Contract.h"

#include "Timestamp.h"


enum class ServiceStatus {
  CHANGED,
  CHECKED,
  NOT_APPLICABLE
};


using RegisterId = uint64_t;

constexpr RegisterId kInvalidDefaultRegisterId = 0;


struct TimeRegister {
  Timestamp m_start;
  Timestamp m_stop;
  UserId m_userId;
};


class Register {
public:


protected:
  RegisterId m_id;
  ContractId m_contractId;
  VehicleId m_vehicleId;
  UserId m_userId;

  std::string m_title;
  std::string m_description;


  float m_amountCost;
  float m_amountIncome;
  

  std::vector<TimeRegister> m_timeRegisters;
  uint64_t m_date;
  uint32_t m_km;


 
  // Fluids
  ServiceStatus m_engineOil;
  ServiceStatus m_brakeFluid;
  ServiceStatus m_coolant;
  ServiceStatus m_transmissionOil;
  ServiceStatus m_differentialOil;
  ServiceStatus m_transferCaseOil;
  ServiceStatus m_powerSteeringFluid;
  ServiceStatus m_acRefrigerant;

  // Ignition & Filters
  ServiceStatus m_sparkPlugs;
  ServiceStatus m_engineAirFilter;
  ServiceStatus m_cabinAirFilter;
  ServiceStatus m_fuelFilter;
  ServiceStatus m_engineOilFilter;
  ServiceStatus m_transmissionOilFilter;

  // Timing & Engine Components
  ServiceStatus m_timingBeltOrChain;
  ServiceStatus m_timingTensioner;
  ServiceStatus m_driveBelt;
  ServiceStatus m_waterPump;

  // Brakes
  ServiceStatus m_brakePads;
  ServiceStatus m_brakeDiscs;

  // Electrical
  ServiceStatus m_battery;

  // Misc
  ServiceStatus m_wiperBlades;
};
