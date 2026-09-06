#define NOMINMAX
#define WIN32_LEAN_AND_MEAN

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#pragma comment(lib, "Ws2_32.lib")

namespace cppvm {

constexpr int kInvalidId = 0;
const std::string kRoleCustomer = "customer";
const std::string kRoleTechnician = "technician";
const std::string kRoleAdmin = "admin";

struct User {
  int id = kInvalidId;
  std::string name;
  std::string email;
  std::string passwordHash;
  std::string role = kRoleCustomer;
};

struct Vehicle {
  int id = kInvalidId;
  std::string brand;
  std::string model;
  std::string vin;
  std::string firstRegistration;
  std::string engineOil;
  std::string gearboxOil;
  std::string diffOil;
  std::string coolant;
  std::string fuel;
  std::string engineCode;
  std::string licensePlate;
  std::string lastOpenedAt;
  std::vector<int> assignedUserIds;
};

struct Order {
  int id = kInvalidId;
  int vehicleId = kInvalidId;
  std::string title;
  std::string description;
  std::string date;
  bool isClosed = false;
  std::string closedAt;
  std::string lastOpenedAt;
  std::vector<int> attachedVehicleIds;
};

struct Cost {
  int id = kInvalidId;
  int orderId = kInvalidId;
  std::string description;
  double amount = 0.0;
  double saleAmount = 0.0;
  std::string person;
  std::string date;
};

struct WorkTime {
  int id = kInvalidId;
  int orderId = kInvalidId;
  std::string description;
  double hours = 0.0;
  std::string person;
  std::string date;
};

struct Income {
  int id = kInvalidId;
  int orderId = kInvalidId;
  std::string description;
  double amount = 0.0;
  std::string person;
  std::string date;
};

struct Totals {
  double cost = 0.0;
  double income = 0.0;
  double hours = 0.0;

  double result() const { return income - cost; }
};

std::string trim(const std::string& value) {
  const auto first = std::find_if_not(value.begin(), value.end(), [](unsigned char ch) {
    return std::isspace(ch) != 0;
  });
  const auto last = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char ch) {
    return std::isspace(ch) != 0;
  }).base();
  if (first >= last) {
    return "";
  }
  return std::string(first, last);
}

std::string toLower(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
    return static_cast<char>(std::tolower(ch));
  });
  return value;
}

bool startsWith(const std::string& value, const std::string& prefix) {
  return value.rfind(prefix, 0) == 0;
}

bool endsWith(const std::string& value, const std::string& suffix) {
  return value.size() >= suffix.size() &&
         value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

std::string htmlEscape(const std::string& value) {
  std::string output;
  output.reserve(value.size());
  for (char ch : value) {
    switch (ch) {
      case '&': output += "&amp;"; break;
      case '<': output += "&lt;"; break;
      case '>': output += "&gt;"; break;
      case '"': output += "&quot;"; break;
      case '\'': output += "&#39;"; break;
      default: output += ch; break;
    }
  }
  return output;
}

std::string replaceAll(std::string value, char from, char to) {
  std::replace(value.begin(), value.end(), from, to);
  return value;
}

std::string nowInput() {
  auto now = std::chrono::system_clock::now();
  std::time_t currentTime = std::chrono::system_clock::to_time_t(now);
  std::tm localTime{};
  localtime_s(&localTime, &currentTime);
  std::ostringstream output;
  output << std::put_time(&localTime, "%Y-%m-%dT%H:%M");
  return output.str();
}

std::string displayDate(const std::string& value) {
  if (value.empty()) {
    return "-";
  }
  return replaceAll(value, 'T', ' ');
}

double parseAmount(std::string value) {
  value = trim(replaceAll(value, ',', '.'));
  if (value.empty()) {
    return 0.0;
  }
  try {
    return std::stod(value);
  } catch (...) {
    return 0.0;
  }
}

int parseInt(const std::string& value) {
  try {
    return std::stoi(value);
  } catch (...) {
    return kInvalidId;
  }
}

std::string formatDecimal(double value, int precision = 2) {
  std::ostringstream output;
  output << std::fixed << std::setprecision(precision) << value;
  return replaceAll(output.str(), '.', ',');
}

std::string roleLabel(const std::string& role) {
  if (role == kRoleAdmin) {
    return "Admin";
  }
  if (role == kRoleTechnician) {
    return "Techniker";
  }
  return "Kunde";
}

bool isValidRole(const std::string& role) {
  return role == kRoleCustomer || role == kRoleTechnician || role == kRoleAdmin;
}

bool canManageUsers(const User& user) {
  return user.role == kRoleAdmin;
}

bool canModifyVehicles(const User& user) {
  return user.role == kRoleAdmin || user.role == kRoleTechnician;
}

bool canAccessAllVehicles(const User& user) {
  return user.role == kRoleAdmin || user.role == kRoleTechnician;
}

std::string displayName(const User& user) {
  const auto name = trim(user.name);
  return name.empty() ? user.email : name;
}

std::string vehicleDisplayName(const Vehicle& vehicle) {
  const auto combined = trim(vehicle.brand + " " + vehicle.model);
  return combined.empty() ? "Unbenanntes Fahrzeug" : combined;
}

std::string hexEncode(const std::string& value) {
  static constexpr char digits[] = "0123456789ABCDEF";
  std::string output;
  output.reserve(value.size() * 2);
  for (unsigned char ch : value) {
    output.push_back(digits[ch >> 4]);
    output.push_back(digits[ch & 0x0F]);
  }
  return output;
}

int hexValue(char ch) {
  if (ch >= '0' && ch <= '9') return ch - '0';
  if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
  if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
  return -1;
}

std::string hexDecode(const std::string& value) {
  if (value.size() % 2 != 0) {
    return "";
  }
  std::string output;
  output.reserve(value.size() / 2);
  for (std::size_t i = 0; i < value.size(); i += 2) {
    const int high = hexValue(value[i]);
    const int low = hexValue(value[i + 1]);
    if (high < 0 || low < 0) {
      return "";
    }
    output.push_back(static_cast<char>((high << 4) | low));
  }
  return output;
}

std::vector<std::string> splitTab(const std::string& line) {
  std::vector<std::string> parts;
  std::string current;
  for (char ch : line) {
    if (ch == '\t') {
      parts.push_back(current);
      current.clear();
    } else {
      current.push_back(ch);
    }
  }
  parts.push_back(current);
  return parts;
}

std::string hashPassword(const std::string& password) {
  constexpr std::uint64_t offset = 1469598103934665603ULL;
  constexpr std::uint64_t prime = 1099511628211ULL;
  std::uint64_t hash = offset;
  const std::string salted = "vehicle-manager-cpp:" + password;
  for (unsigned char ch : salted) {
    hash ^= ch;
    hash *= prime;
  }
  std::ostringstream output;
  output << std::hex << std::setw(16) << std::setfill('0') << hash;
  return output.str();
}

class Database {
public:
  explicit Database(std::filesystem::path path) : path_(std::move(path)) {}

  const std::filesystem::path& path() const { return path_; }

  bool load() {
    users.clear();
    vehicles.clear();
    orders.clear();
    costs.clear();
    times.clear();
    incomes.clear();

    std::ifstream input(path_, std::ios::binary);
    if (!input) {
      recomputeNextIds();
      return true;
    }

    std::string line;
    while (std::getline(input, line)) {
      if (line.empty()) {
        continue;
      }
      const auto parts = splitTab(line);
      if (parts.empty()) {
        continue;
      }
      const auto& type = parts[0];

      if (type == "U" && parts.size() >= 6) {
        User item;
        item.id = parseInt(parts[1]);
        item.name = hexDecode(parts[2]);
        item.email = hexDecode(parts[3]);
        item.passwordHash = hexDecode(parts[4]);
        item.role = isValidRole(parts[5]) ? parts[5] : kRoleCustomer;
        users.push_back(item);
      } else if (type == "V" && parts.size() >= 13) {
        Vehicle item;
        item.id = parseInt(parts[1]);
        item.brand = hexDecode(parts[2]);
        item.model = hexDecode(parts[3]);
        item.vin = hexDecode(parts[4]);
        item.firstRegistration = hexDecode(parts[5]);
        item.engineOil = hexDecode(parts[6]);
        item.gearboxOil = hexDecode(parts[7]);
        item.diffOil = hexDecode(parts[8]);
        item.coolant = hexDecode(parts[9]);
        item.fuel = hexDecode(parts[10]);
        item.engineCode = hexDecode(parts[11]);
        item.licensePlate = hexDecode(parts[12]);
        if (parts.size() >= 14) {
          item.lastOpenedAt = hexDecode(parts[13]);
        }
        vehicles.push_back(item);
      } else if (type == "VU" && parts.size() >= 3) {
        pendingVehicleUsers_.push_back({parseInt(parts[1]), parseInt(parts[2])});
      } else if (type == "O" && parts.size() >= 9) {
        Order item;
        item.id = parseInt(parts[1]);
        item.vehicleId = parseInt(parts[2]);
        item.title = hexDecode(parts[3]);
        item.description = hexDecode(parts[4]);
        item.date = hexDecode(parts[5]);
        item.isClosed = parts[6] == "1";
        item.closedAt = hexDecode(parts[7]);
        item.lastOpenedAt = hexDecode(parts[8]);
        orders.push_back(item);
      } else if (type == "OA" && parts.size() >= 3) {
        pendingOrderVehicles_.push_back({parseInt(parts[1]), parseInt(parts[2])});
      } else if (type == "C" && parts.size() >= 8) {
        Cost item;
        item.id = parseInt(parts[1]);
        item.orderId = parseInt(parts[2]);
        item.description = hexDecode(parts[3]);
        item.amount = parseAmount(parts[4]);
        item.saleAmount = parseAmount(parts[5]);
        item.person = hexDecode(parts[6]);
        item.date = hexDecode(parts[7]);
        costs.push_back(item);
      } else if (type == "T" && parts.size() >= 7) {
        WorkTime item;
        item.id = parseInt(parts[1]);
        item.orderId = parseInt(parts[2]);
        item.description = hexDecode(parts[3]);
        item.hours = parseAmount(parts[4]);
        item.person = hexDecode(parts[5]);
        item.date = hexDecode(parts[6]);
        times.push_back(item);
      } else if (type == "I" && parts.size() >= 7) {
        Income item;
        item.id = parseInt(parts[1]);
        item.orderId = parseInt(parts[2]);
        item.description = hexDecode(parts[3]);
        item.amount = parseAmount(parts[4]);
        item.person = hexDecode(parts[5]);
        item.date = hexDecode(parts[6]);
        incomes.push_back(item);
      }
    }

    applyPendingRelations();
    recomputeNextIds();
    return true;
  }

  bool save() const {
    const auto tempPath = path_.string() + ".tmp";
    std::ofstream output(tempPath, std::ios::binary | std::ios::trunc);
    if (!output) {
      return false;
    }

    for (const auto& user : users) {
      output << "U\t" << user.id << '\t'
             << hexEncode(user.name) << '\t'
             << hexEncode(user.email) << '\t'
             << hexEncode(user.passwordHash) << '\t'
             << user.role << '\n';
    }
    for (const auto& vehicle : vehicles) {
      output << "V\t" << vehicle.id << '\t'
             << hexEncode(vehicle.brand) << '\t'
             << hexEncode(vehicle.model) << '\t'
             << hexEncode(vehicle.vin) << '\t'
             << hexEncode(vehicle.firstRegistration) << '\t'
             << hexEncode(vehicle.engineOil) << '\t'
             << hexEncode(vehicle.gearboxOil) << '\t'
             << hexEncode(vehicle.diffOil) << '\t'
             << hexEncode(vehicle.coolant) << '\t'
             << hexEncode(vehicle.fuel) << '\t'
             << hexEncode(vehicle.engineCode) << '\t'
             << hexEncode(vehicle.licensePlate) << '\t'
             << hexEncode(vehicle.lastOpenedAt) << '\n';
      for (int userId : vehicle.assignedUserIds) {
        output << "VU\t" << vehicle.id << '\t' << userId << '\n';
      }
    }
    for (const auto& order : orders) {
      output << "O\t" << order.id << '\t'
             << order.vehicleId << '\t'
             << hexEncode(order.title) << '\t'
             << hexEncode(order.description) << '\t'
             << hexEncode(order.date) << '\t'
             << (order.isClosed ? "1" : "0") << '\t'
             << hexEncode(order.closedAt) << '\t'
             << hexEncode(order.lastOpenedAt) << '\n';
      for (int vehicleId : order.attachedVehicleIds) {
        output << "OA\t" << order.id << '\t' << vehicleId << '\n';
      }
    }
    for (const auto& cost : costs) {
      output << "C\t" << cost.id << '\t'
             << cost.orderId << '\t'
             << hexEncode(cost.description) << '\t'
             << cost.amount << '\t'
             << cost.saleAmount << '\t'
             << hexEncode(cost.person) << '\t'
             << hexEncode(cost.date) << '\n';
    }
    for (const auto& time : times) {
      output << "T\t" << time.id << '\t'
             << time.orderId << '\t'
             << hexEncode(time.description) << '\t'
             << time.hours << '\t'
             << hexEncode(time.person) << '\t'
             << hexEncode(time.date) << '\n';
    }
    for (const auto& income : incomes) {
      output << "I\t" << income.id << '\t'
             << income.orderId << '\t'
             << hexEncode(income.description) << '\t'
             << income.amount << '\t'
             << hexEncode(income.person) << '\t'
             << hexEncode(income.date) << '\n';
    }

    output.close();
    if (!output) {
      return false;
    }

    std::error_code error;
    std::filesystem::remove(path_, error);
    error.clear();
    std::filesystem::rename(tempPath, path_, error);
    return !error;
  }

  void ensureDefaultAdmin() {
    if (users.empty()) {
      User admin;
      admin.id = nextUserId++;
      admin.name = "Admin";
      admin.email = "admin@example.com";
      admin.passwordHash = hashPassword("admin");
      admin.role = kRoleAdmin;
      users.push_back(admin);
      save();
      return;
    }

    const bool hasAdmin = std::any_of(users.begin(), users.end(), [](const User& user) {
      return user.role == kRoleAdmin;
    });
    if (!hasAdmin) {
      users.front().role = kRoleAdmin;
      save();
    }
  }

  User* findUser(int id) {
    auto found = std::find_if(users.begin(), users.end(), [id](const User& item) {
      return item.id == id;
    });
    return found == users.end() ? nullptr : &*found;
  }

  const User* findUser(int id) const {
    auto found = std::find_if(users.begin(), users.end(), [id](const User& item) {
      return item.id == id;
    });
    return found == users.end() ? nullptr : &*found;
  }

  User* findUserByEmail(const std::string& email) {
    auto found = std::find_if(users.begin(), users.end(), [&email](const User& item) {
      return item.email == email;
    });
    return found == users.end() ? nullptr : &*found;
  }

  Vehicle* findVehicle(int id) {
    auto found = std::find_if(vehicles.begin(), vehicles.end(), [id](const Vehicle& item) {
      return item.id == id;
    });
    return found == vehicles.end() ? nullptr : &*found;
  }

  const Vehicle* findVehicle(int id) const {
    auto found = std::find_if(vehicles.begin(), vehicles.end(), [id](const Vehicle& item) {
      return item.id == id;
    });
    return found == vehicles.end() ? nullptr : &*found;
  }

  Order* findOrder(int id) {
    auto found = std::find_if(orders.begin(), orders.end(), [id](const Order& item) {
      return item.id == id;
    });
    return found == orders.end() ? nullptr : &*found;
  }

  const Order* findOrder(int id) const {
    auto found = std::find_if(orders.begin(), orders.end(), [id](const Order& item) {
      return item.id == id;
    });
    return found == orders.end() ? nullptr : &*found;
  }

  Cost* findCost(int id) {
    auto found = std::find_if(costs.begin(), costs.end(), [id](const Cost& item) {
      return item.id == id;
    });
    return found == costs.end() ? nullptr : &*found;
  }

  WorkTime* findTime(int id) {
    auto found = std::find_if(times.begin(), times.end(), [id](const WorkTime& item) {
      return item.id == id;
    });
    return found == times.end() ? nullptr : &*found;
  }

  Income* findIncome(int id) {
    auto found = std::find_if(incomes.begin(), incomes.end(), [id](const Income& item) {
      return item.id == id;
    });
    return found == incomes.end() ? nullptr : &*found;
  }

  int createUserId() { return nextUserId++; }
  int createVehicleId() { return nextVehicleId++; }
  int createOrderId() { return nextOrderId++; }
  int createCostId() { return nextCostId++; }
  int createTimeId() { return nextTimeId++; }
  int createIncomeId() { return nextIncomeId++; }

  std::vector<User> users;
  std::vector<Vehicle> vehicles;
  std::vector<Order> orders;
  std::vector<Cost> costs;
  std::vector<WorkTime> times;
  std::vector<Income> incomes;

private:
  void applyPendingRelations() {
    for (const auto& relation : pendingVehicleUsers_) {
      Vehicle* vehicle = findVehicle(relation.first);
      if (vehicle && findUser(relation.second)) {
        if (std::find(vehicle->assignedUserIds.begin(), vehicle->assignedUserIds.end(), relation.second) ==
            vehicle->assignedUserIds.end()) {
          vehicle->assignedUserIds.push_back(relation.second);
        }
      }
    }
    for (const auto& relation : pendingOrderVehicles_) {
      Order* order = findOrder(relation.first);
      if (order && findVehicle(relation.second)) {
        if (std::find(order->attachedVehicleIds.begin(), order->attachedVehicleIds.end(), relation.second) ==
            order->attachedVehicleIds.end()) {
          order->attachedVehicleIds.push_back(relation.second);
        }
      }
    }
    pendingVehicleUsers_.clear();
    pendingOrderVehicles_.clear();
  }

  void recomputeNextIds() {
    nextUserId = nextVehicleId = nextOrderId = nextCostId = nextTimeId = nextIncomeId = 1;
    for (const auto& item : users) nextUserId = std::max(nextUserId, item.id + 1);
    for (const auto& item : vehicles) nextVehicleId = std::max(nextVehicleId, item.id + 1);
    for (const auto& item : orders) nextOrderId = std::max(nextOrderId, item.id + 1);
    for (const auto& item : costs) nextCostId = std::max(nextCostId, item.id + 1);
    for (const auto& item : times) nextTimeId = std::max(nextTimeId, item.id + 1);
    for (const auto& item : incomes) nextIncomeId = std::max(nextIncomeId, item.id + 1);
  }

  std::filesystem::path path_;
  int nextUserId = 1;
  int nextVehicleId = 1;
  int nextOrderId = 1;
  int nextCostId = 1;
  int nextTimeId = 1;
  int nextIncomeId = 1;
  std::vector<std::pair<int, int>> pendingVehicleUsers_;
  std::vector<std::pair<int, int>> pendingOrderVehicles_;
};

std::vector<User*> sortedUsers(Database& db) {
  std::vector<User*> result;
  for (auto& user : db.users) {
    result.push_back(&user);
  }
  std::sort(result.begin(), result.end(), [](const User* left, const User* right) {
    const auto leftName = toLower(displayName(*left));
    const auto rightName = toLower(displayName(*right));
    if (leftName != rightName) return leftName < rightName;
    if (left->email != right->email) return left->email < right->email;
    return left->id < right->id;
  });
  return result;
}

std::vector<User*> staffUsers(Database& db) {
  std::vector<User*> result;
  for (auto& user : db.users) {
    if (user.role == kRoleTechnician || user.role == kRoleAdmin) {
      result.push_back(&user);
    }
  }
  std::sort(result.begin(), result.end(), [](const User* left, const User* right) {
    return toLower(displayName(*left)) < toLower(displayName(*right));
  });
  return result;
}

bool userAssignedToVehicle(const Vehicle& vehicle, int userId) {
  return std::find(vehicle.assignedUserIds.begin(), vehicle.assignedUserIds.end(), userId) !=
         vehicle.assignedUserIds.end();
}

bool canAccessVehicle(const Database& db, const User& user, const Vehicle& vehicle) {
  if (canAccessAllVehicles(user)) {
    return true;
  }
  return userAssignedToVehicle(vehicle, user.id);
}

bool canAccessOrder(const Database& db, const User& user, const Order& order) {
  const Vehicle* vehicle = db.findVehicle(order.vehicleId);
  return vehicle && canAccessVehicle(db, user, *vehicle);
}

std::vector<Vehicle*> visibleVehicles(Database& db, const User& user) {
  std::vector<Vehicle*> result;
  for (auto& vehicle : db.vehicles) {
    if (canAccessVehicle(db, user, vehicle)) {
      result.push_back(&vehicle);
    }
  }
  std::sort(result.begin(), result.end(), [](const Vehicle* left, const Vehicle* right) {
    if (left->lastOpenedAt != right->lastOpenedAt) return left->lastOpenedAt > right->lastOpenedAt;
    if (toLower(left->brand) != toLower(right->brand)) return toLower(left->brand) < toLower(right->brand);
    if (toLower(left->model) != toLower(right->model)) return toLower(left->model) < toLower(right->model);
    return left->id < right->id;
  });
  return result;
}

std::vector<Order*> visibleOrders(Database& db, const User& user, bool showClosed) {
  std::vector<Order*> result;
  for (auto& order : db.orders) {
    if (order.isClosed == showClosed && canAccessOrder(db, user, order)) {
      result.push_back(&order);
    }
  }
  std::sort(result.begin(), result.end(), [](const Order* left, const Order* right) {
    if (left->lastOpenedAt != right->lastOpenedAt) return left->lastOpenedAt > right->lastOpenedAt;
    if (left->date != right->date) return left->date > right->date;
    return left->id > right->id;
  });
  return result;
}

std::vector<Order*> ordersForVehicle(Database& db, int vehicleId, bool closed) {
  std::vector<Order*> result;
  for (auto& order : db.orders) {
    if (order.vehicleId == vehicleId && order.isClosed == closed) {
      result.push_back(&order);
    }
  }
  std::sort(result.begin(), result.end(), [](const Order* left, const Order* right) {
    if (left->lastOpenedAt != right->lastOpenedAt) return left->lastOpenedAt > right->lastOpenedAt;
    if (left->date != right->date) return left->date > right->date;
    return left->id > right->id;
  });
  return result;
}

std::vector<Order*> attachedToOrders(Database& db, const User& user, int vehicleId) {
  std::vector<Order*> result;
  for (auto& order : db.orders) {
    if (std::find(order.attachedVehicleIds.begin(), order.attachedVehicleIds.end(), vehicleId) !=
            order.attachedVehicleIds.end() &&
        canAccessOrder(db, user, order)) {
      result.push_back(&order);
    }
  }
  std::sort(result.begin(), result.end(), [](const Order* left, const Order* right) {
    if (left->lastOpenedAt != right->lastOpenedAt) return left->lastOpenedAt > right->lastOpenedAt;
    if (left->date != right->date) return left->date > right->date;
    return left->id > right->id;
  });
  return result;
}

std::vector<Cost*> costsForOrder(Database& db, int orderId) {
  std::vector<Cost*> result;
  for (auto& item : db.costs) {
    if (item.orderId == orderId) result.push_back(&item);
  }
  std::sort(result.begin(), result.end(), [](const Cost* left, const Cost* right) {
    return left->date > right->date;
  });
  return result;
}

std::vector<WorkTime*> timesForOrder(Database& db, int orderId) {
  std::vector<WorkTime*> result;
  for (auto& item : db.times) {
    if (item.orderId == orderId) result.push_back(&item);
  }
  std::sort(result.begin(), result.end(), [](const WorkTime* left, const WorkTime* right) {
    return left->date > right->date;
  });
  return result;
}

std::vector<Income*> incomesForOrder(Database& db, int orderId) {
  std::vector<Income*> result;
  for (auto& item : db.incomes) {
    if (item.orderId == orderId) result.push_back(&item);
  }
  std::sort(result.begin(), result.end(), [](const Income* left, const Income* right) {
    return left->date > right->date;
  });
  return result;
}

Totals directOrderTotals(Database& db, const Order& order) {
  Totals totals;
  for (const auto& cost : db.costs) {
    if (cost.orderId == order.id) totals.cost += cost.amount;
  }
  for (const auto& income : db.incomes) {
    if (income.orderId == order.id) totals.income += income.amount;
  }
  for (const auto& time : db.times) {
    if (time.orderId == order.id) totals.hours += time.hours;
  }
  return totals;
}

Totals ownVehicleTotals(Database& db, const Vehicle& vehicle) {
  Totals totals;
  for (const auto& order : db.orders) {
    if (order.vehicleId != vehicle.id) {
      continue;
    }
    const Totals direct = directOrderTotals(db, order);
    totals.cost += direct.cost;
    totals.income += direct.income;
    totals.hours += direct.hours;
  }
  return totals;
}

Totals orderTotals(Database& db, const Order& order) {
  Totals totals = directOrderTotals(db, order);
  for (int vehicleId : order.attachedVehicleIds) {
    if (const Vehicle* vehicle = db.findVehicle(vehicleId)) {
      const Totals attached = ownVehicleTotals(db, *vehicle);
      totals.cost += attached.cost;
      totals.income += attached.income;
      totals.hours += attached.hours;
    }
  }
  return totals;
}

Totals orderTotalsForUser(Database& db, const User& user, const Order& order) {
  Totals totals = directOrderTotals(db, order);
  for (int vehicleId : order.attachedVehicleIds) {
    if (const Vehicle* vehicle = db.findVehicle(vehicleId)) {
      if (canAccessVehicle(db, user, *vehicle)) {
        const Totals attached = ownVehicleTotals(db, *vehicle);
        totals.cost += attached.cost;
        totals.income += attached.income;
        totals.hours += attached.hours;
      }
    }
  }
  return totals;
}

Totals vehicleTotals(Database& db, const Vehicle& vehicle) {
  Totals totals = ownVehicleTotals(db, vehicle);
  std::vector<int> seenAttachedVehicles;
  for (const auto& order : db.orders) {
    if (order.vehicleId != vehicle.id) {
      continue;
    }
    for (int attachedVehicleId : order.attachedVehicleIds) {
      if (std::find(seenAttachedVehicles.begin(), seenAttachedVehicles.end(), attachedVehicleId) !=
          seenAttachedVehicles.end()) {
        continue;
      }
      seenAttachedVehicles.push_back(attachedVehicleId);
      if (const Vehicle* attached = db.findVehicle(attachedVehicleId)) {
        const Totals attachedTotals = ownVehicleTotals(db, *attached);
        totals.cost += attachedTotals.cost;
        totals.income += attachedTotals.income;
        totals.hours += attachedTotals.hours;
      }
    }
  }
  return totals;
}

Totals vehicleTotalsForUser(Database& db, const User& user, const Vehicle& vehicle) {
  if (canAccessAllVehicles(user)) {
    return vehicleTotals(db, vehicle);
  }
  Totals totals = ownVehicleTotals(db, vehicle);
  std::vector<int> seenAttachedVehicles;
  for (const auto& order : db.orders) {
    if (order.vehicleId != vehicle.id) {
      continue;
    }
    for (int attachedVehicleId : order.attachedVehicleIds) {
      if (std::find(seenAttachedVehicles.begin(), seenAttachedVehicles.end(), attachedVehicleId) !=
          seenAttachedVehicles.end()) {
        continue;
      }
      seenAttachedVehicles.push_back(attachedVehicleId);
      if (const Vehicle* attached = db.findVehicle(attachedVehicleId)) {
        if (canAccessVehicle(db, user, *attached)) {
          const Totals attachedTotals = ownVehicleTotals(db, *attached);
          totals.cost += attachedTotals.cost;
          totals.income += attachedTotals.income;
          totals.hours += attachedTotals.hours;
        }
      }
    }
  }
  return totals;
}

std::vector<User*> selectableUsersForOrder(Database& db, const Order& order) {
  std::map<int, User*> uniqueUsers;
  if (const Vehicle* vehicle = db.findVehicle(order.vehicleId)) {
    for (int userId : vehicle->assignedUserIds) {
      if (User* user = db.findUser(userId)) uniqueUsers[user->id] = user;
    }
  }
  for (int vehicleId : order.attachedVehicleIds) {
    if (const Vehicle* vehicle = db.findVehicle(vehicleId)) {
      for (int userId : vehicle->assignedUserIds) {
        if (User* user = db.findUser(userId)) uniqueUsers[user->id] = user;
      }
    }
  }

  if (uniqueUsers.empty()) {
    return sortedUsers(db);
  }

  std::vector<User*> result;
  for (auto& [id, user] : uniqueUsers) {
    result.push_back(user);
  }
  std::sort(result.begin(), result.end(), [](const User* left, const User* right) {
    return toLower(displayName(*left)) < toLower(displayName(*right));
  });
  return result;
}

std::string userList(Database& db, const std::vector<int>& userIds) {
  std::vector<std::string> names;
  for (int userId : userIds) {
    if (const User* user = db.findUser(userId)) {
      names.push_back(displayName(*user));
    }
  }
  std::sort(names.begin(), names.end(), [](const std::string& left, const std::string& right) {
    return toLower(left) < toLower(right);
  });
  if (names.empty()) {
    return "Keine Benutzer";
  }
  std::ostringstream output;
  for (std::size_t i = 0; i < names.size(); ++i) {
    if (i) output << ", ";
    output << names[i];
  }
  return output.str();
}

std::string urlDecode(const std::string& value) {
  std::string output;
  output.reserve(value.size());
  for (std::size_t i = 0; i < value.size(); ++i) {
    if (value[i] == '+') {
      output.push_back(' ');
    } else if (value[i] == '%' && i + 2 < value.size()) {
      const int high = hexValue(value[i + 1]);
      const int low = hexValue(value[i + 2]);
      if (high >= 0 && low >= 0) {
        output.push_back(static_cast<char>((high << 4) | low));
        i += 2;
      } else {
        output.push_back(value[i]);
      }
    } else {
      output.push_back(value[i]);
    }
  }
  return output;
}

std::unordered_map<std::string, std::vector<std::string>> parseKeyValues(const std::string& body) {
  std::unordered_map<std::string, std::vector<std::string>> values;
  std::size_t start = 0;
  while (start <= body.size()) {
    const auto end = body.find('&', start);
    const auto part = body.substr(start, end == std::string::npos ? std::string::npos : end - start);
    const auto equals = part.find('=');
    const auto key = urlDecode(part.substr(0, equals));
    const auto value = equals == std::string::npos ? "" : urlDecode(part.substr(equals + 1));
    if (!key.empty()) {
      values[key].push_back(value);
    }
    if (end == std::string::npos) {
      break;
    }
    start = end + 1;
  }
  return values;
}

std::string formValue(const std::unordered_map<std::string, std::vector<std::string>>& form,
                      const std::string& key,
                      const std::string& fallback = "") {
  const auto found = form.find(key);
  if (found == form.end() || found->second.empty()) {
    return fallback;
  }
  return found->second.front();
}

std::vector<int> formIds(const std::unordered_map<std::string, std::vector<std::string>>& form,
                         const std::string& key) {
  std::vector<int> ids;
  const auto found = form.find(key);
  if (found == form.end()) {
    return ids;
  }
  for (const auto& value : found->second) {
    const int id = parseInt(value);
    if (id != kInvalidId && std::find(ids.begin(), ids.end(), id) == ids.end()) {
      ids.push_back(id);
    }
  }
  return ids;
}

struct Request {
  std::string method;
  std::string path;
  std::string query;
  std::string body;
  std::map<std::string, std::string> headers;
  std::map<std::string, std::string> cookies;
  std::unordered_map<std::string, std::vector<std::string>> form;
  std::unordered_map<std::string, std::vector<std::string>> queryValues;
};

struct Response {
  int status = 200;
  std::string statusText = "OK";
  std::string contentType = "text/html; charset=utf-8";
  std::map<std::string, std::string> headers;
  std::string body;
};

struct Session {
  int userId = kInvalidId;
  std::vector<std::pair<std::string, std::string>> flashes;
};

std::string randomSessionId() {
  static std::mt19937_64 rng(std::random_device{}());
  static constexpr char alphabet[] = "0123456789abcdef";
  std::uniform_int_distribution<int> distribution(0, 15);
  std::string value(48, '0');
  for (char& ch : value) {
    ch = alphabet[distribution(rng)];
  }
  return value;
}

std::string optionTag(const std::string& value, const std::string& label, const std::string& current) {
  std::ostringstream output;
  output << "<option value=\"" << htmlEscape(value) << "\"";
  if (value == current) {
    output << " selected";
  }
  output << ">" << htmlEscape(label) << "</option>";
  return output.str();
}

std::string roleSelect(const std::string& id, const std::string& current) {
  std::ostringstream output;
  output << "<select id=\"" << htmlEscape(id) << "\" name=\"role\" required>";
  output << optionTag(kRoleCustomer, "Kunde", current);
  output << optionTag(kRoleTechnician, "Techniker", current);
  output << optionTag(kRoleAdmin, "Admin", current);
  output << "</select>";
  return output.str();
}

std::string renderPersonSelect(const std::string& fieldId,
                               const std::string& label,
                               const std::string& selected,
                               const std::string& fieldClass,
                               const std::vector<User*>& users) {
  std::ostringstream output;
  output << "<div class=\"" << htmlEscape(fieldClass) << "\">";
  output << "<label for=\"" << htmlEscape(fieldId) << "\">" << htmlEscape(label) << "</label>";
  if (!users.empty()) {
    output << "<select id=\"" << htmlEscape(fieldId) << "\" name=\"person\" required>";
    output << "<option value=\"\"" << (selected.empty() ? " selected" : "") << ">Benutzer auswählen</option>";
    bool selectedFound = false;
    for (const User* user : users) {
      const auto name = displayName(*user);
      const bool isSelected = selected == name || selected == user->email;
      selectedFound = selectedFound || isSelected;
      output << "<option value=\"" << htmlEscape(name) << "\"";
      if (isSelected) output << " selected";
      output << ">" << htmlEscape(name) << "</option>";
    }
    if (!selected.empty() && !selectedFound) {
      output << "<option value=\"" << htmlEscape(selected) << "\" selected>"
             << htmlEscape(selected) << " (bisheriger Wert)</option>";
    }
    output << "</select>";
  } else {
    output << "<input id=\"" << htmlEscape(fieldId) << "\" type=\"text\" name=\"person\" value=\""
           << htmlEscape(selected) << "\" required>";
    output << "<p class=\"hint\">Lege zuerst einen passenden Benutzer an, um hier auswählen zu können.</p>";
  }
  output << "</div>";
  return output.str();
}

bool parseIdPath(const std::string& path,
                 const std::string& prefix,
                 const std::string& suffix,
                 int& id) {
  if (!startsWith(path, prefix) || !endsWith(path, suffix)) {
    return false;
  }
  const auto idPart = path.substr(prefix.size(), path.size() - prefix.size() - suffix.size());
  if (idPart.empty() || !std::all_of(idPart.begin(), idPart.end(), [](unsigned char ch) {
        return std::isdigit(ch) != 0;
      })) {
    return false;
  }
  id = parseInt(idPart);
  return id != kInvalidId;
}

bool parseTwoIdPath(const std::string& path,
                    const std::string& prefix,
                    const std::string& middle,
                    int& firstId,
                    int& secondId) {
  if (!startsWith(path, prefix)) {
    return false;
  }
  const auto remaining = path.substr(prefix.size());
  const auto middlePos = remaining.find(middle);
  if (middlePos == std::string::npos) {
    return false;
  }
  const auto first = remaining.substr(0, middlePos);
  const auto second = remaining.substr(middlePos + middle.size());
  if (first.empty() || second.empty()) {
    return false;
  }
  firstId = parseInt(first);
  secondId = parseInt(second);
  return firstId != kInvalidId && secondId != kInvalidId;
}

std::string pdfEscape(const std::string& value) {
  std::string output;
  for (char ch : value) {
    if (ch == '(' || ch == ')' || ch == '\\') {
      output.push_back('\\');
    }
    if (static_cast<unsigned char>(ch) < 32) {
      output.push_back(' ');
    } else {
      output.push_back(ch);
    }
  }
  return output;
}

std::string buildSimplePdf(const std::string& title, const std::vector<std::string>& lines) {
  std::ostringstream content;
  content << "BT\n/F1 14 Tf\n50 790 Td\n(" << pdfEscape(title) << ") Tj\n";
  content << "/F1 10 Tf\n0 -24 Td\n";
  for (const auto& line : lines) {
    content << "(" << pdfEscape(line) << ") Tj\n0 -16 Td\n";
  }
  content << "ET\n";
  const auto stream = content.str();

  std::vector<std::string> objects;
  objects.push_back("<< /Type /Catalog /Pages 2 0 R >>");
  objects.push_back("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
  objects.push_back("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>");
  objects.push_back("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  objects.push_back("<< /Length " + std::to_string(stream.size()) + " >>\nstream\n" + stream + "endstream");

  std::ostringstream output;
  output << "%PDF-1.4\n";
  std::vector<long long> offsets;
  offsets.push_back(0);
  for (std::size_t i = 0; i < objects.size(); ++i) {
    offsets.push_back(static_cast<long long>(output.tellp()));
    output << (i + 1) << " 0 obj\n" << objects[i] << "\nendobj\n";
  }
  const long long xrefOffset = static_cast<long long>(output.tellp());
  output << "xref\n0 " << (objects.size() + 1) << "\n";
  output << "0000000000 65535 f \n";
  for (std::size_t i = 1; i < offsets.size(); ++i) {
    output << std::setw(10) << std::setfill('0') << offsets[i] << " 00000 n \n";
  }
  output << "trailer\n<< /Size " << (objects.size() + 1) << " /Root 1 0 R >>\n";
  output << "startxref\n" << xrefOffset << "\n%%EOF\n";
  return output.str();
}

class Application {
public:
  explicit Application(Database database) : db_(std::move(database)) {}

  Response handle(Request request) {
    Response response;
    Session& session = ensureSession(request, response);
    User* user = currentUser(session);

    if (request.path == "/login") {
      return request.method == "POST"
                 ? loginPost(request, response, session)
                 : htmlResponse(response, loginPage(request, session));
    }

    if (!user) {
      flash(session, "warning", "Bitte zuerst anmelden.");
      return redirect(response, "/login");
    }

    if (request.path == "/logout") {
      session.userId = kInvalidId;
      flash(session, "info", "Du wurdest abgemeldet.");
      return redirect(response, "/login");
    }
    if (request.path == "/" && request.method == "GET") {
      return htmlResponse(response, indexPage(request, session, *user));
    }
    if (request.path == "/orders" && request.method == "GET") {
      return htmlResponse(response, ordersPage(request, session, *user));
    }
    if (request.path == "/users") {
      if (!canManageUsers(*user)) {
        flash(session, "danger", "Nur Admins können Benutzer verwalten.");
        return redirect(response, "/");
      }
      return request.method == "POST"
                 ? createUserPost(request, response, session)
                 : htmlResponse(response, usersPage(request, session, *user));
    }
    if (request.path == "/add_vehicle") {
      if (!canModifyVehicles(*user)) {
        return denied(response, session);
      }
      return request.method == "POST"
                 ? addVehiclePost(request, response, session)
                 : htmlResponse(response, vehicleFormPage(request, session, *user, nullptr, "/add_vehicle", "Fahrzeug hinzufügen"));
    }

    int id = kInvalidId;
    int secondId = kInvalidId;

    if (parseIdPath(request.path, "/users/", "/edit", id) && request.method == "POST") {
      if (!canManageUsers(*user)) return denied(response, session);
      return editUserPost(request, response, session, *user, id);
    }
    if (parseIdPath(request.path, "/users/", "/delete", id) && request.method == "POST") {
      if (!canManageUsers(*user)) return denied(response, session);
      return deleteUserPost(response, session, *user, id);
    }
    if (parseIdPath(request.path, "/vehicle/", "/edit", id)) {
      Vehicle* vehicle = db_.findVehicle(id);
      if (!vehicle) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessVehicle(db_, *user, *vehicle)) return denied(response, session);
      return request.method == "POST"
                 ? editVehiclePost(request, response, session, *vehicle)
                 : htmlResponse(response, vehicleFormPage(request, session, *user, vehicle, "/vehicle/" + std::to_string(id) + "/edit", "Fahrzeug bearbeiten"));
    }
    if (parseIdPath(request.path, "/vehicle/", "/delete", id) && request.method == "POST") {
      Vehicle* vehicle = db_.findVehicle(id);
      if (!vehicle) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessVehicle(db_, *user, *vehicle)) return denied(response, session);
      return deleteVehiclePost(response, session, *vehicle);
    }
    if (parseIdPath(request.path, "/vehicle/", "/add_order", id)) {
      Vehicle* vehicle = db_.findVehicle(id);
      if (!vehicle) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessVehicle(db_, *user, *vehicle)) return denied(response, session);
      return request.method == "POST"
                 ? addOrderPost(request, response, session, *vehicle)
                 : htmlResponse(response, addOrderPage(request, session, *user, *vehicle));
    }
    if (parseIdPath(request.path, "/vehicle/", "/print", id) && request.method == "GET") {
      Vehicle* vehicle = db_.findVehicle(id);
      if (!vehicle) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessVehicle(db_, *user, *vehicle)) return denied(response, session);
      return vehiclePdf(response, *vehicle);
    }
    if (parseIdPath(request.path, "/vehicle/", "", id) && request.method == "GET") {
      Vehicle* vehicle = db_.findVehicle(id);
      if (!vehicle) return notFound(response, request, session, *user);
      if (!canAccessVehicle(db_, *user, *vehicle)) return denied(response, session);
      vehicle->lastOpenedAt = nowInput();
      db_.save();
      return htmlResponse(response, vehiclePage(request, session, *user, *vehicle));
    }

    if (parseIdPath(request.path, "/order/", "/edit", id)) {
      Order* order = db_.findOrder(id);
      if (!order) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      if (order->isClosed) return closedOrder(response, session, *order);
      return request.method == "POST"
                 ? editOrderPost(request, response, session, *order)
                 : htmlResponse(response, editOrderPage(request, session, *user, *order));
    }
    if (parseIdPath(request.path, "/order/", "/close", id) && request.method == "POST") {
      Order* order = db_.findOrder(id);
      if (!order) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      return closeOrderPost(response, session, *order);
    }
    if (parseTwoIdPath(request.path, "/order/", "/detach_vehicle/", id, secondId) && request.method == "POST") {
      Order* order = db_.findOrder(id);
      Vehicle* vehicle = db_.findVehicle(secondId);
      if (!order || !vehicle) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order) || !canAccessVehicle(db_, *user, *vehicle)) {
        return denied(response, session);
      }
      return detachVehiclePost(response, session, *order, *vehicle);
    }
    if (parseIdPath(request.path, "/order/", "/print", id) && request.method == "GET") {
      Order* order = db_.findOrder(id);
      if (!order) return notFound(response, request, session, *user);
      if (!canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      return orderPdf(response, *order);
    }
    if (parseIdPath(request.path, "/order/", "", id)) {
      Order* order = db_.findOrder(id);
      if (!order) return notFound(response, request, session, *user);
      if (!canAccessOrder(db_, *user, *order)) return denied(response, session);
      return request.method == "POST"
                 ? orderActionPost(request, response, session, *user, *order)
                 : htmlResponse(response, orderPage(request, session, *user, *order));
    }

    if (parseIdPath(request.path, "/edit_cost/", "", id)) {
      Cost* cost = db_.findCost(id);
      if (!cost) return notFound(response, request, session, *user);
      Order* order = db_.findOrder(cost->orderId);
      if (!order || !canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      if (order->isClosed) return closedOrder(response, session, *order);
      return request.method == "POST"
                 ? editCostPost(request, response, session, *cost)
                 : htmlResponse(response, editCostPage(request, session, *user, *cost));
    }
    if (parseIdPath(request.path, "/edit_time/", "", id)) {
      WorkTime* time = db_.findTime(id);
      if (!time) return notFound(response, request, session, *user);
      Order* order = db_.findOrder(time->orderId);
      if (!order || !canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      if (order->isClosed) return closedOrder(response, session, *order);
      return request.method == "POST"
                 ? editTimePost(request, response, session, *time)
                 : htmlResponse(response, editTimePage(request, session, *user, *time));
    }
    if (parseIdPath(request.path, "/edit_income/", "", id)) {
      Income* income = db_.findIncome(id);
      if (!income) return notFound(response, request, session, *user);
      Order* order = db_.findOrder(income->orderId);
      if (!order || !canModifyVehicles(*user) || !canAccessOrder(db_, *user, *order)) return denied(response, session);
      if (order->isClosed) return closedOrder(response, session, *order);
      return request.method == "POST"
                 ? editIncomePost(request, response, session, *income)
                 : htmlResponse(response, editIncomePage(request, session, *user, *income));
    }
    if (parseIdPath(request.path, "/delete_cost/", "", id) && request.method == "POST") {
      Cost* cost = db_.findCost(id);
      if (!cost) return notFound(response, request, session, *user);
      return deleteCostPost(response, session, *user, *cost);
    }
    if (parseIdPath(request.path, "/delete_time/", "", id) && request.method == "POST") {
      WorkTime* time = db_.findTime(id);
      if (!time) return notFound(response, request, session, *user);
      return deleteTimePost(response, session, *user, *time);
    }
    if (parseIdPath(request.path, "/delete_income/", "", id) && request.method == "POST") {
      Income* income = db_.findIncome(id);
      if (!income) return notFound(response, request, session, *user);
      return deleteIncomePost(response, session, *user, *income);
    }

    return notFound(response, request, session, *user);
  }

private:
  Session& ensureSession(const Request& request, Response& response) {
    std::string sessionId;
    const auto foundCookie = request.cookies.find("sid");
    if (foundCookie != request.cookies.end()) {
      sessionId = foundCookie->second;
    }
    if (sessionId.empty() || sessions_.find(sessionId) == sessions_.end()) {
      sessionId = randomSessionId();
      sessions_[sessionId] = Session{};
      response.headers["Set-Cookie"] = "sid=" + sessionId + "; Path=/; HttpOnly; SameSite=Lax";
    }
    return sessions_[sessionId];
  }

  User* currentUser(Session& session) {
    if (session.userId == kInvalidId) {
      return nullptr;
    }
    User* user = db_.findUser(session.userId);
    if (!user) {
      session.userId = kInvalidId;
    }
    return user;
  }

  void flash(Session& session, const std::string& category, const std::string& message) {
    session.flashes.push_back({category, message});
  }

  Response htmlResponse(Response response, std::string body) {
    response.body = std::move(body);
    response.contentType = "text/html; charset=utf-8";
    return response;
  }

  Response redirect(Response response, const std::string& location) {
    response.status = 303;
    response.statusText = "See Other";
    response.headers["Location"] = location;
    response.body = "<!doctype html><html><body>Weiterleitung...</body></html>";
    return response;
  }

  Response denied(Response response, Session& session) {
    flash(session, "danger", "Dafür hast du keine Berechtigung.");
    return redirect(response, "/");
  }

  Response closedOrder(Response response, Session& session, const Order& order) {
    flash(session, "warning", "Dieser Auftrag ist abgeschlossen und kann nicht mehr geändert werden.");
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  Response notFound(Response response, const Request& request, Session& session, const User& user) {
    response.status = 404;
    response.statusText = "Not Found";
    return htmlResponse(response, layout(request, session, &user, "Nicht gefunden",
                                       "<div class=\"card\"><h1>Nicht gefunden</h1><p>Die gewünschte Seite existiert nicht.</p></div>"));
  }

  std::string layout(const Request& request,
                     Session& session,
                     const User* user,
                     const std::string& title,
                     const std::string& content) {
    std::ostringstream output;
    output << "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">";
    output << "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">";
    output << "<title>" << htmlEscape(title) << " - Vehicle Manager C++</title>";
    output << css();
    output << "</head><body>";

    if (user) {
      output << "<header class=\"topbar\"><div class=\"topbar-inner\">";
      output << "<a class=\"brand\" href=\"/\">Vehicle Manager C++</a><nav class=\"nav\">";
      const bool vehicleActive = request.path == "/" || startsWith(request.path, "/vehicle") || request.path == "/add_vehicle";
      const bool orderActive = startsWith(request.path, "/order") || startsWith(request.path, "/edit_");
      output << "<a href=\"/\" class=\"" << (vehicleActive ? "active" : "") << "\">Fahrzeuge</a>";
      output << "<a href=\"/orders\" class=\"" << (orderActive ? "active" : "") << "\">Aufträge</a>";
      if (canManageUsers(*user)) {
        output << "<a href=\"/users\" class=\"" << (startsWith(request.path, "/users") ? "active" : "") << "\">Benutzer</a>";
      }
      output << "<span class=\"nav-user\">" << htmlEscape(displayName(*user)) << " · " << htmlEscape(roleLabel(user->role)) << "</span>";
      output << "<a href=\"/logout\">Abmelden</a>";
      output << "</nav></div></header>";
    }

    output << "<main class=\"page\">";
    for (const auto& item : session.flashes) {
      output << "<div class=\"alert alert-" << htmlEscape(item.first) << "\">"
             << htmlEscape(item.second) << "</div>";
    }
    session.flashes.clear();
    output << content;
    output << "</main></body></html>";
    return output.str();
  }

  std::string css() const {
    return R"CSS(
<style>
:root {
  --bg: #f4f6f8;
  --surface: #ffffff;
  --surface-soft: #f8fafc;
  --text: #17202a;
  --muted: #667085;
  --line: #e4e7ec;
  --primary: #155eef;
  --primary-dark: #004eeb;
  --success: #067647;
  --success-soft: #ecfdf3;
  --warning: #b54708;
  --warning-soft: #fffaeb;
  --danger: #b42318;
  --danger-soft: #fef3f2;
  --info-soft: #eff8ff;
  --shadow: 0 12px 32px rgba(16, 24, 40, .08);
  --radius: 14px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--text);
  background: var(--bg);
  font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }
h1, h2, h3 { margin-top: 0; line-height: 1.2; }
h1 { font-size: clamp(1.6rem, 3vw, 2.25rem); }
h2 { font-size: 1.25rem; }
p { margin-top: 0; }
form { margin: 0; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #101828;
  color: white;
  box-shadow: 0 3px 12px rgba(16, 24, 40, .18);
}
.topbar-inner {
  width: min(1180px, calc(100% - 32px));
  min-height: 64px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.brand { color: white; font-size: 1.05rem; font-weight: 750; }
.brand:hover { text-decoration: none; }
.nav { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.nav a { color: #d0d5dd; padding: 8px 11px; border-radius: 8px; font-weight: 600; }
.nav a:hover, .nav a.active { color: white; background: rgba(255,255,255,.1); text-decoration: none; }
.nav-user { color: #f2f4f7; padding: 8px 11px; font-weight: 700; }
.page { width: min(1180px, calc(100% - 32px)); margin: 28px auto 60px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 22px; }
.page-header p { color: var(--muted); margin-bottom: 0; }
.actions { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; }
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px;
}
.card + .card { margin-top: 18px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.card-header h2 { margin-bottom: 0; }
.grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 18px; }
.span-3 { grid-column: span 3; }
.span-4 { grid-column: span 4; }
.span-6 { grid-column: span 6; }
.span-8 { grid-column: span 8; }
.span-12 { grid-column: span 12; }
.stat { padding: 18px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.stat-label { color: var(--muted); font-size: .85rem; font-weight: 650; }
.stat-value { margin-top: 5px; font-size: 1.45rem; font-weight: 760; }
.positive { color: var(--success); }
.negative { color: var(--danger); }
.btn {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 9px;
  padding: 8px 14px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
}
.btn:hover { text-decoration: none; filter: brightness(.97); }
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: var(--primary-dark); }
.btn-secondary { border-color: var(--line); background: var(--surface); }
.btn-success { background: var(--success); color: white; }
.btn-danger { background: var(--danger); color: white; }
.btn-sm { min-height: 34px; padding: 5px 10px; font-size: .88rem; }
.field { margin-bottom: 16px; }
.field:last-child { margin-bottom: 0; }
label { display: block; margin-bottom: 6px; font-weight: 700; }
input, textarea, select {
  width: 100%;
  border: 1px solid #d0d5dd;
  border-radius: 9px;
  padding: 10px 12px;
  background: white;
  color: var(--text);
  font: inherit;
}
textarea { min-height: 110px; resize: vertical; }
input:focus, textarea:focus, select:focus {
  outline: 3px solid rgba(21,94,239,.13);
  border-color: var(--primary);
}
.hint { color: var(--muted); font-size: .84rem; margin-top: 5px; }
.tabs {
  display: flex;
  gap: 5px;
  padding: 5px;
  margin-bottom: 18px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--surface-soft);
  width: fit-content;
}
.tab { padding: 8px 13px; border-radius: 8px; color: var(--muted); font-weight: 700; }
.tab.active { background: white; color: var(--text); box-shadow: 0 1px 4px rgba(16,24,40,.1); }
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: .78rem;
  font-weight: 750;
}
.badge-open { background: var(--success-soft); color: var(--success); }
.badge-closed { background: #f2f4f7; color: #475467; }
.list { display: grid; gap: 11px; }
.list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--line);
  border-radius: 11px;
  padding: 14px 16px;
  background: white;
}
.list-item:hover { border-color: #b2ccff; }
.list-title { font-weight: 750; color: var(--text); }
.list-meta { color: var(--muted); font-size: .87rem; margin-top: 2px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  text-align: left;
  font-size: .78rem;
  text-transform: uppercase;
  letter-spacing: .04em;
}
td { padding: 12px; border-bottom: 1px solid var(--line); vertical-align: middle; }
tr:last-child td { border-bottom: 0; }
.number { text-align: right; white-space: nowrap; }
.details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 24px; }
.detail { display: flex; justify-content: space-between; gap: 18px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.detail-label { color: var(--muted); }
.detail-value { font-weight: 650; text-align: right; }
.alert { margin-bottom: 18px; border: 1px solid; border-radius: 10px; padding: 12px 14px; }
.alert-success { color: var(--success); background: var(--success-soft); border-color: #abefc6; }
.alert-warning { color: var(--warning); background: var(--warning-soft); border-color: #fedf89; }
.alert-danger { color: var(--danger); background: var(--danger-soft); border-color: #fecdca; }
.alert-info { color: #175cd3; background: var(--info-soft); border-color: #b2ddff; }
.empty { padding: 36px 18px; border: 1px dashed #cfd4dc; border-radius: 11px; color: var(--muted); text-align: center; background: var(--surface-soft); }
.section-title { margin: 28px 0 12px; }
.login-shell { width: min(440px, 100%); margin: 70px auto; }
@media (max-width: 820px) {
  .span-3, .span-4, .span-6, .span-8 { grid-column: span 12; }
  .page-header { flex-direction: column; }
  .details { grid-template-columns: 1fr; }
  .topbar-inner { align-items: flex-start; padding: 13px 0; flex-direction: column; gap: 8px; }
  .topbar { position: static; }
  .page { margin-top: 20px; }
}
@media (max-width: 560px) {
  .page, .topbar-inner { width: min(100% - 20px, 1180px); }
  .card { padding: 16px; }
  .list-item { align-items: flex-start; flex-direction: column; }
  .actions { width: 100%; }
  .actions .btn { flex: 1; }
}
</style>
)CSS";
  }

  std::string loginPage(const Request& request, Session& session) {
    std::ostringstream body;
    body << "<div class=\"login-shell\"><div class=\"card\">";
    body << "<h1>Anmelden</h1>";
    body << "<form method=\"post\" action=\"/login\">";
    body << "<div class=\"field\"><label for=\"email\">E-Mail-Adresse</label><input id=\"email\" type=\"email\" name=\"email\" required autofocus></div>";
    body << "<div class=\"field\"><label for=\"password\">Passwort</label><input id=\"password\" type=\"password\" name=\"password\" required></div>";
    body << "<button class=\"btn btn-primary\" type=\"submit\">Anmelden</button>";
    body << "</form>";
    body << "<p class=\"hint\" style=\"margin-top:16px\">Erster Start: admin@example.com / admin</p>";
    body << "</div></div>";
    return layout(request, session, nullptr, "Login", body.str());
  }

  Response loginPost(const Request& request, Response response, Session& session) {
    const auto email = trim(formValue(request.form, "email"));
    const auto password = formValue(request.form, "password");
    User* user = db_.findUserByEmail(email);
    if (!user || user->passwordHash != hashPassword(password)) {
      flash(session, "danger", "E-Mail-Adresse oder Passwort ist falsch.");
      return redirect(response, "/login");
    }
    session.userId = user->id;
    flash(session, "success", "Willkommen, " + displayName(*user) + ".");
    return redirect(response, "/");
  }

  std::string indexPage(const Request& request, Session& session, const User& user) {
    const auto vehicles = visibleVehicles(db_, user);
    const auto openOrders = visibleOrders(db_, user, false);
    const auto closedOrders = visibleOrders(db_, user, true);

    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Fahrzeuge</h1>";
    body << "<p>Alle Fahrzeuge und ihre aktuellen Aufträge auf einen Blick.</p></div>";
    if (canModifyVehicles(user)) {
      body << "<div class=\"actions\"><a class=\"btn btn-primary\" href=\"/add_vehicle\">Fahrzeug hinzufügen</a></div>";
    }
    body << "</div>";

    body << "<div class=\"grid\" style=\"margin-bottom:22px\">";
    stat(body, "Fahrzeuge", std::to_string(vehicles.size()), "span-4");
    stat(body, "Offene Aufträge", std::to_string(openOrders.size()), "span-4 positive");
    stat(body, "Geschlossene Aufträge", std::to_string(closedOrders.size()), "span-4");
    body << "</div>";

    body << "<div class=\"card\"><div class=\"card-header\"><h2>Fahrzeugliste</h2></div>";
    if (vehicles.empty()) {
      body << "<div class=\"empty\">";
      if (canModifyVehicles(user)) {
        body << "Noch keine Fahrzeuge vorhanden.<br>Lege das erste Fahrzeug über Fahrzeug hinzufügen an.";
      } else {
        body << "Dir sind noch keine Fahrzeuge zugeordnet.";
      }
      body << "</div>";
    } else {
      body << "<div class=\"list\">";
      for (const Vehicle* vehicle : vehicles) {
        const auto openCount = std::count_if(db_.orders.begin(), db_.orders.end(), [vehicle](const Order& order) {
          return order.vehicleId == vehicle->id && !order.isClosed;
        });
        body << "<a class=\"list-item\" href=\"/vehicle/" << vehicle->id << "\"><div>";
        body << "<div class=\"list-title\">" << htmlEscape(vehicleDisplayName(*vehicle)) << "</div>";
        body << "<div class=\"list-meta\">" << htmlEscape(vehicle->licensePlate.empty() ? "Kein Kennzeichen" : vehicle->licensePlate)
             << " · FIN/VIN: " << htmlEscape(vehicle->vin.empty() ? "-" : vehicle->vin)
             << " · Benutzer: " << htmlEscape(userList(db_, vehicle->assignedUserIds)) << "</div>";
        body << "</div><span class=\"badge " << (openCount ? "badge-open" : "badge-closed") << "\">"
             << openCount << " offen</span></a>";
      }
      body << "</div>";
    }
    body << "</div>";
    return layout(request, session, &user, "Fahrzeuge", body.str());
  }

  std::string ordersPage(const Request& request, Session& session, const User& user) {
    const bool showClosed = formValue(request.queryValues, "status") == "closed";
    const auto orders = visibleOrders(db_, user, showClosed);
    const auto openOrders = visibleOrders(db_, user, false);
    const auto closedOrders = visibleOrders(db_, user, true);

    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Aufträge</h1>";
    body << "<p>Offene und abgeschlossene Aufträge.</p></div></div>";
    body << "<div class=\"tabs\">";
    body << "<a class=\"tab " << (!showClosed ? "active" : "") << "\" href=\"/orders\">Offen (" << openOrders.size() << ")</a>";
    body << "<a class=\"tab " << (showClosed ? "active" : "") << "\" href=\"/orders?status=closed\">Geschlossen (" << closedOrders.size() << ")</a>";
    body << "</div>";
    body << "<div class=\"card\"><div class=\"card-header\"><h2>"
         << (showClosed ? "Geschlossene Aufträge" : "Offene Aufträge") << "</h2></div>";
    if (orders.empty()) {
      body << "<div class=\"empty\">Keine " << (showClosed ? "geschlossenen" : "offenen") << " Aufträge vorhanden.</div>";
    } else {
      body << "<div class=\"list\">";
      for (const Order* order : orders) {
        const Vehicle* vehicle = db_.findVehicle(order->vehicleId);
        body << "<a class=\"list-item\" href=\"/order/" << order->id << "\"><div>";
        body << "<div class=\"list-title\">" << htmlEscape(order->title) << "</div>";
        body << "<div class=\"list-meta\">" << htmlEscape(vehicle ? vehicleDisplayName(*vehicle) : "Unbekanntes Fahrzeug")
             << " · angelegt " << htmlEscape(displayDate(order->date));
        if (order->isClosed) body << " · abgeschlossen " << htmlEscape(displayDate(order->closedAt));
        body << "</div></div><span class=\"badge " << (order->isClosed ? "badge-closed" : "badge-open") << "\">"
             << (order->isClosed ? "Geschlossen" : "Offen") << "</span></a>";
      }
      body << "</div>";
    }
    body << "</div>";
    return layout(request, session, &user, "Aufträge", body.str());
  }

  std::string usersPage(const Request& request, Session& session, const User& current) {
    const auto users = sortedUsers(db_);
    const auto customerCount = std::count_if(db_.users.begin(), db_.users.end(), [](const User& user) { return user.role == kRoleCustomer; });
    const auto technicianCount = std::count_if(db_.users.begin(), db_.users.end(), [](const User& user) { return user.role == kRoleTechnician; });
    const auto adminCount = std::count_if(db_.users.begin(), db_.users.end(), [](const User& user) { return user.role == kRoleAdmin; });

    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Benutzer</h1><p>Benutzer, Rollen und Fahrzeug-Zuordnungen.</p></div></div>";
    body << "<div class=\"grid\" style=\"margin-bottom:22px\">";
    stat(body, "Benutzer", std::to_string(users.size()), "span-3");
    stat(body, "Kunden", std::to_string(customerCount), "span-3");
    stat(body, "Techniker", std::to_string(technicianCount), "span-3");
    stat(body, "Admins", std::to_string(adminCount), "span-3");
    body << "</div>";

    body << "<section class=\"card\" style=\"margin-bottom:22px\"><div class=\"card-header\"><h2>Benutzer anlegen</h2></div>";
    body << "<form method=\"post\" action=\"/users\" class=\"grid\">";
    body << "<div class=\"field span-6\"><label for=\"name\">Name</label><input id=\"name\" type=\"text\" name=\"name\" required></div>";
    body << "<div class=\"field span-6\"><label for=\"email\">E-Mail-Adresse</label><input id=\"email\" type=\"email\" name=\"email\" required></div>";
    body << "<div class=\"field span-4\"><label for=\"password\">Passwort</label><input id=\"password\" type=\"password\" name=\"password\" required></div>";
    body << "<div class=\"field span-4\"><label for=\"passwordConfirm\">Passwort wiederholen</label><input id=\"passwordConfirm\" type=\"password\" name=\"passwordConfirm\" required></div>";
    body << "<div class=\"field span-4\"><label for=\"role\">Rolle</label>" << roleSelect("role", kRoleCustomer) << "</div>";
    body << "<div class=\"actions span-12\"><button class=\"btn btn-primary\" type=\"submit\">Benutzer anlegen</button></div>";
    body << "</form></section>";

    body << "<div class=\"card\"><div class=\"card-header\"><h2>Benutzerliste</h2></div>";
    if (users.empty()) {
      body << "<div class=\"empty\">Noch keine Benutzer vorhanden.</div>";
    } else {
      body << "<div class=\"list\">";
      for (const User* user : users) {
        body << "<div class=\"list-item\"><div style=\"flex:1\">";
        body << "<div class=\"list-title\">" << htmlEscape(displayName(*user))
             << "<span class=\"badge badge-open\" style=\"margin-left:8px\">" << htmlEscape(roleLabel(user->role)) << "</span></div>";
        body << "<div class=\"list-meta\">" << htmlEscape(user->email) << "</div>";
        body << "<form id=\"edit_user_" << user->id << "\" method=\"post\" action=\"/users/" << user->id << "/edit\" class=\"grid\" style=\"margin-top:12px\">";
        body << "<div class=\"field span-4\"><label for=\"name_" << user->id << "\">Name</label><input id=\"name_" << user->id << "\" type=\"text\" name=\"name\" value=\"" << htmlEscape(user->name) << "\" required></div>";
        body << "<div class=\"field span-4\"><label for=\"email_" << user->id << "\">E-Mail-Adresse</label><input id=\"email_" << user->id << "\" type=\"email\" name=\"email\" value=\"" << htmlEscape(user->email) << "\" required></div>";
        body << "<div class=\"field span-4\"><label for=\"role_" << user->id << "\">Rolle</label>" << roleSelect("role_" + std::to_string(user->id), user->role) << "</div>";
        body << "<div class=\"field span-6\"><label for=\"password_" << user->id << "\">Neues Passwort</label><input id=\"password_" << user->id << "\" type=\"password\" name=\"password\"></div>";
        body << "<div class=\"field span-6\"><label for=\"passwordConfirm_" << user->id << "\">Neues Passwort wiederholen</label><input id=\"passwordConfirm_" << user->id << "\" type=\"password\" name=\"passwordConfirm\"></div>";
        body << "</form>";
        body << "<div class=\"list-meta\">";
        bool hasVehicle = false;
        for (const auto& vehicle : db_.vehicles) {
          if (userAssignedToVehicle(vehicle, user->id)) {
            if (!hasVehicle) body << "Fahrzeuge: ";
            if (hasVehicle) body << ", ";
            body << "<a href=\"/vehicle/" << vehicle.id << "\">" << htmlEscape(vehicleDisplayName(vehicle)) << "</a>";
            hasVehicle = true;
          }
        }
        if (!hasVehicle) body << "Noch keinem Fahrzeug zugeordnet.";
        body << "</div></div><div class=\"actions\">";
        body << "<button class=\"btn btn-secondary btn-sm\" type=\"submit\" form=\"edit_user_" << user->id << "\">Speichern</button>";
        if (current.id != user->id) {
          body << "<form method=\"post\" action=\"/users/" << user->id << "/delete\" onsubmit=\"return confirm('Benutzer wirklich löschen?')\">";
          body << "<button class=\"btn btn-danger btn-sm\" type=\"submit\">Löschen</button></form>";
        }
        body << "</div></div>";
      }
      body << "</div>";
    }
    body << "</div>";
    return layout(request, session, &current, "Benutzer", body.str());
  }

  void stat(std::ostringstream& body, const std::string& label, const std::string& value, const std::string& classes) {
    body << "<div class=\"stat " << htmlEscape(classes) << "\"><div class=\"stat-label\">"
         << htmlEscape(label) << "</div><div class=\"stat-value\">" << htmlEscape(value) << "</div></div>";
  }

  Response createUserPost(const Request& request, Response response, Session& session) {
    const auto name = trim(formValue(request.form, "name"));
    const auto email = trim(formValue(request.form, "email"));
    const auto password = formValue(request.form, "password");
    const auto passwordConfirm = formValue(request.form, "passwordConfirm");
    std::string role = formValue(request.form, "role", kRoleCustomer);
    if (!isValidRole(role)) role = kRoleCustomer;
    if (name.empty() || email.empty() || password.empty()) {
      flash(session, "danger", "Name, E-Mail-Adresse und Passwort sind Pflichtfelder.");
      return redirect(response, "/users");
    }
    if (password != passwordConfirm) {
      flash(session, "danger", "Die Passwörter stimmen nicht überein.");
      return redirect(response, "/users");
    }
    if (db_.findUserByEmail(email)) {
      flash(session, "danger", "Diese E-Mail-Adresse ist bereits vergeben.");
      return redirect(response, "/users");
    }
    User user;
    user.id = db_.createUserId();
    user.name = name;
    user.email = email;
    user.passwordHash = hashPassword(password);
    user.role = role;
    db_.users.push_back(user);
    db_.save();
    flash(session, "success", "Benutzer wurde angelegt.");
    return redirect(response, "/users");
  }

  Response editUserPost(const Request& request, Response response, Session& session, const User& current, int userId) {
    User* user = db_.findUser(userId);
    if (!user) return redirect(response, "/users");

    const auto name = trim(formValue(request.form, "name"));
    const auto email = trim(formValue(request.form, "email"));
    const auto password = formValue(request.form, "password");
    const auto passwordConfirm = formValue(request.form, "passwordConfirm");
    std::string role = formValue(request.form, "role", user->role);
    if (!isValidRole(role)) role = user->role;

    if (name.empty() || email.empty()) {
      flash(session, "danger", "Name und E-Mail-Adresse sind Pflichtfelder.");
      return redirect(response, "/users");
    }
    if (User* existing = db_.findUserByEmail(email); existing && existing->id != user->id) {
      flash(session, "danger", "Diese E-Mail-Adresse ist bereits vergeben.");
      return redirect(response, "/users");
    }
    if (!password.empty() || !passwordConfirm.empty()) {
      if (password != passwordConfirm) {
        flash(session, "danger", "Die Passwörter stimmen nicht überein.");
        return redirect(response, "/users");
      }
      if (password.empty()) {
        flash(session, "danger", "Das Passwort darf nicht leer sein.");
        return redirect(response, "/users");
      }
    }
    if (user->id == current.id && role != kRoleAdmin) {
      flash(session, "danger", "Du kannst dir nicht selbst die Admin-Rolle entziehen.");
      return redirect(response, "/users");
    }
    if (user->role == kRoleAdmin && role != kRoleAdmin && adminCount() <= 1) {
      flash(session, "danger", "Mindestens ein Admin muss erhalten bleiben.");
      return redirect(response, "/users");
    }

    user->name = name;
    user->email = email;
    user->role = role;
    if (!password.empty()) {
      user->passwordHash = hashPassword(password);
    }
    db_.save();
    flash(session, "success", "Benutzer wurde gespeichert.");
    return redirect(response, "/users");
  }

  Response deleteUserPost(Response response, Session& session, const User& current, int userId) {
    User* user = db_.findUser(userId);
    if (!user) return redirect(response, "/users");
    if (user->id == current.id) {
      flash(session, "danger", "Du kannst deinen eigenen Benutzer nicht löschen.");
      return redirect(response, "/users");
    }
    if (user->role == kRoleAdmin && adminCount() <= 1) {
      flash(session, "danger", "Mindestens ein Admin muss erhalten bleiben.");
      return redirect(response, "/users");
    }
    for (auto& vehicle : db_.vehicles) {
      vehicle.assignedUserIds.erase(
          std::remove(vehicle.assignedUserIds.begin(), vehicle.assignedUserIds.end(), userId),
          vehicle.assignedUserIds.end());
    }
    db_.users.erase(std::remove_if(db_.users.begin(), db_.users.end(), [userId](const User& item) {
                      return item.id == userId;
                    }),
                    db_.users.end());
    db_.save();
    flash(session, "success", "Benutzer wurde gelöscht.");
    return redirect(response, "/users");
  }

  int adminCount() const {
    return static_cast<int>(std::count_if(db_.users.begin(), db_.users.end(), [](const User& user) {
      return user.role == kRoleAdmin;
    }));
  }

  std::string vehicleFields(const Vehicle* vehicle) {
    const int selectedUserId = vehicle && !vehicle->assignedUserIds.empty() ? vehicle->assignedUserIds.front() : kInvalidId;
    std::ostringstream body;
    body << "<div class=\"grid\">";
    textField(body, "brand", "Marke", vehicle ? vehicle->brand : "", "span-4", true);
    textField(body, "model", "Modell", vehicle ? vehicle->model : "", "span-4", true);
    textField(body, "licensePlate", "Kennzeichen", vehicle ? vehicle->licensePlate : "", "span-4", false);
    textField(body, "vin", "FIN/VIN", vehicle ? vehicle->vin : "", "span-6", true);
    textField(body, "firstRegistration", "Erstzulassung", vehicle ? vehicle->firstRegistration : "", "span-6", false, "z. B. 05/2018");
    body << "</div>";

    body << "<h2 class=\"section-title\">Benutzer</h2><div class=\"grid\"><div class=\"field span-12\">";
    body << "<label for=\"user_ids\">Benutzer am Fahrzeug</label>";
    const auto users = sortedUsers(db_);
    if (users.empty()) {
      body << "<p class=\"hint\">Noch keine Benutzer vorhanden.</p>";
    } else {
      body << "<select id=\"user_ids\" name=\"user_ids\"><option value=\"\">Kein Benutzer</option>";
      for (const User* user : users) {
        body << "<option value=\"" << user->id << "\"";
        if (user->id == selectedUserId) body << " selected";
        body << ">" << htmlEscape(displayName(*user) + " - " + roleLabel(user->role));
        if (user->email != displayName(*user)) {
          body << " (" << htmlEscape(user->email) << ")";
        }
        body << "</option>";
      }
      body << "</select>";
    }
    body << "</div></div>";

    body << "<h2 class=\"section-title\">Technische Daten</h2><div class=\"grid\">";
    textField(body, "engineOil", "Motoröl", vehicle ? vehicle->engineOil : "", "span-4", false);
    textField(body, "gearboxOil", "Getriebeöl", vehicle ? vehicle->gearboxOil : "", "span-4", false);
    textField(body, "diffOil", "Differentialöl", vehicle ? vehicle->diffOil : "", "span-4", false);
    textField(body, "coolant", "Kühlmittel", vehicle ? vehicle->coolant : "", "span-4", false);
    textField(body, "fuel", "Kraftstoff", vehicle ? vehicle->fuel : "", "span-4", false);
    textField(body, "engineCode", "Motorkennbuchstabe", vehicle ? vehicle->engineCode : "", "span-4", false);
    body << "</div>";
    return body.str();
  }

  void textField(std::ostringstream& body,
                 const std::string& name,
                 const std::string& label,
                 const std::string& value,
                 const std::string& span,
                 bool required,
                 const std::string& placeholder = "") {
    body << "<div class=\"field " << htmlEscape(span) << "\"><label for=\"" << htmlEscape(name) << "\">"
         << htmlEscape(label) << "</label><input id=\"" << htmlEscape(name) << "\" type=\"text\" name=\""
         << htmlEscape(name) << "\" value=\"" << htmlEscape(value) << "\"";
    if (!placeholder.empty()) body << " placeholder=\"" << htmlEscape(placeholder) << "\"";
    if (required) body << " required";
    body << "></div>";
  }

  std::string vehicleFormPage(const Request& request,
                              Session& session,
                              const User& user,
                              const Vehicle* vehicle,
                              const std::string& action,
                              const std::string& title) {
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>" << htmlEscape(title) << "</h1>";
    body << "<p>Fahrzeugdaten und Benutzer-Zuordnung.</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"" << htmlEscape(action) << "\">";
    body << vehicleFields(vehicle);
    body << "<div class=\"actions\" style=\"margin-top:22px\"><button class=\"btn btn-primary\" type=\"submit\">Speichern</button>";
    if (vehicle) {
      body << "<a class=\"btn btn-secondary\" href=\"/vehicle/" << vehicle->id << "\">Abbrechen</a>";
    } else {
      body << "<a class=\"btn btn-secondary\" href=\"/\">Abbrechen</a>";
    }
    body << "</div></form></div>";
    if (vehicle) {
      body << "<div class=\"card\"><h2>Fahrzeug löschen</h2>";
      body << "<form method=\"post\" action=\"/vehicle/" << vehicle->id << "/delete\" onsubmit=\"return confirm('Fahrzeug wirklich löschen?')\">";
      body << "<button class=\"btn btn-danger\" type=\"submit\">Fahrzeug löschen</button></form></div>";
    }
    return layout(request, session, &user, title, body.str());
  }

  void fillVehicleFromForm(Vehicle& vehicle, const Request& request) {
    vehicle.brand = trim(formValue(request.form, "brand"));
    vehicle.model = trim(formValue(request.form, "model"));
    vehicle.vin = trim(formValue(request.form, "vin"));
    vehicle.firstRegistration = trim(formValue(request.form, "firstRegistration"));
    vehicle.engineOil = trim(formValue(request.form, "engineOil"));
    vehicle.gearboxOil = trim(formValue(request.form, "gearboxOil"));
    vehicle.diffOil = trim(formValue(request.form, "diffOil"));
    vehicle.coolant = trim(formValue(request.form, "coolant"));
    vehicle.fuel = trim(formValue(request.form, "fuel"));
    vehicle.engineCode = trim(formValue(request.form, "engineCode"));
    vehicle.licensePlate = trim(formValue(request.form, "licensePlate"));
    vehicle.assignedUserIds.clear();
    for (int userId : formIds(request.form, "user_ids")) {
      if (db_.findUser(userId)) {
        vehicle.assignedUserIds.push_back(userId);
      }
    }
  }

  Response addVehiclePost(const Request& request, Response response, Session& session) {
    Vehicle vehicle;
    vehicle.id = db_.createVehicleId();
    fillVehicleFromForm(vehicle, request);
    db_.vehicles.push_back(vehicle);
    db_.save();
    flash(session, "success", "Fahrzeug wurde angelegt.");
    return redirect(response, "/vehicle/" + std::to_string(vehicle.id));
  }

  Response editVehiclePost(const Request& request, Response response, Session& session, Vehicle& vehicle) {
    fillVehicleFromForm(vehicle, request);
    db_.save();
    flash(session, "success", "Fahrzeug wurde gespeichert.");
    return redirect(response, "/vehicle/" + std::to_string(vehicle.id));
  }

  Response deleteVehiclePost(Response response, Session& session, Vehicle& vehicle) {
    const bool hasClosedOrder = std::any_of(db_.orders.begin(), db_.orders.end(), [&vehicle](const Order& order) {
      return order.vehicleId == vehicle.id && order.isClosed;
    });
    if (hasClosedOrder) {
      flash(session, "danger", "Fahrzeuge mit abgeschlossenen Aufträgen können nicht gelöscht werden.");
      return redirect(response, "/vehicle/" + std::to_string(vehicle.id));
    }

    std::vector<int> orderIds;
    for (const auto& order : db_.orders) {
      if (order.vehicleId == vehicle.id) {
        orderIds.push_back(order.id);
      }
    }
    db_.costs.erase(std::remove_if(db_.costs.begin(), db_.costs.end(), [&orderIds](const Cost& item) {
                      return std::find(orderIds.begin(), orderIds.end(), item.orderId) != orderIds.end();
                    }),
                    db_.costs.end());
    db_.times.erase(std::remove_if(db_.times.begin(), db_.times.end(), [&orderIds](const WorkTime& item) {
                     return std::find(orderIds.begin(), orderIds.end(), item.orderId) != orderIds.end();
                   }),
                   db_.times.end());
    db_.incomes.erase(std::remove_if(db_.incomes.begin(), db_.incomes.end(), [&orderIds](const Income& item) {
                       return std::find(orderIds.begin(), orderIds.end(), item.orderId) != orderIds.end();
                     }),
                     db_.incomes.end());
    db_.orders.erase(std::remove_if(db_.orders.begin(), db_.orders.end(), [&orderIds](const Order& order) {
                       return std::find(orderIds.begin(), orderIds.end(), order.id) != orderIds.end();
                     }),
                     db_.orders.end());
    for (auto& order : db_.orders) {
      order.attachedVehicleIds.erase(
          std::remove(order.attachedVehicleIds.begin(), order.attachedVehicleIds.end(), vehicle.id),
          order.attachedVehicleIds.end());
    }
    const int vehicleId = vehicle.id;
    db_.vehicles.erase(std::remove_if(db_.vehicles.begin(), db_.vehicles.end(), [vehicleId](const Vehicle& item) {
                         return item.id == vehicleId;
                       }),
                       db_.vehicles.end());
    db_.save();
    flash(session, "success", "Fahrzeug wurde gelöscht.");
    return redirect(response, "/");
  }

  std::string vehiclePage(const Request& request, Session& session, const User& user, const Vehicle& vehicle) {
    const auto totals = vehicleTotalsForUser(db_, user, vehicle);
    const auto openOrders = ordersForVehicle(db_, vehicle.id, false);
    const auto closedOrders = ordersForVehicle(db_, vehicle.id, true);
    const bool showClosed = formValue(request.queryValues, "tab") == "closed";
    const auto attachedOrders = attachedToOrders(db_, user, vehicle.id);

    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>" << htmlEscape(vehicleDisplayName(vehicle)) << "</h1>";
    body << "<p>" << htmlEscape(vehicle.licensePlate.empty() ? "Kein Kennzeichen" : vehicle.licensePlate)
         << " · FIN/VIN: " << htmlEscape(vehicle.vin.empty() ? "-" : vehicle.vin)
         << " · Benutzer: " << htmlEscape(userList(db_, vehicle.assignedUserIds)) << "</p></div>";
    body << "<div class=\"actions\">";
    if (canModifyVehicles(user)) {
      body << "<a class=\"btn btn-secondary\" href=\"/vehicle/" << vehicle.id << "/print\">PDF</a>";
      body << "<a class=\"btn btn-secondary\" href=\"/vehicle/" << vehicle.id << "/edit\">Bearbeiten</a>";
      body << "<a class=\"btn btn-primary\" href=\"/vehicle/" << vehicle.id << "/add_order\">Neuer Auftrag</a>";
    }
    body << "</div></div>";

    body << "<div class=\"grid\" style=\"margin-bottom:22px\">";
    stat(body, "Einnahmen", formatDecimal(totals.income) + " EUR", "span-3");
    stat(body, "EK", formatDecimal(totals.cost) + " EUR", "span-3");
    stat(body, "Ergebnis", formatDecimal(totals.result()) + " EUR", totals.result() >= 0 ? "span-3 positive" : "span-3 negative");
    stat(body, "Arbeitszeit", formatDecimal(totals.hours) + " h", "span-3");
    body << "</div>";

    body << "<div class=\"grid\"><section class=\"card span-4\"><div class=\"card-header\"><h2>Fahrzeugdaten</h2></div>";
    body << "<div class=\"details\" style=\"grid-template-columns:1fr\">";
    detail(body, "Erstzulassung", vehicle.firstRegistration);
    detail(body, "Motoröl", vehicle.engineOil);
    detail(body, "Getriebeöl", vehicle.gearboxOil);
    detail(body, "Differentialöl", vehicle.diffOil);
    detail(body, "Kühlmittel", vehicle.coolant);
    detail(body, "Kraftstoff", vehicle.fuel);
    detail(body, "Motorkennbuchstabe", vehicle.engineCode);
    detail(body, "Benutzer", userList(db_, vehicle.assignedUserIds));
    body << "</div></section>";

    body << "<section class=\"card span-8\"><div class=\"card-header\"><h2>Aufträge</h2></div>";
    body << "<div class=\"tabs\">";
    body << "<a class=\"tab " << (!showClosed ? "active" : "") << "\" href=\"/vehicle/" << vehicle.id << "\">Offen (" << openOrders.size() << ")</a>";
    body << "<a class=\"tab " << (showClosed ? "active" : "") << "\" href=\"/vehicle/" << vehicle.id << "?tab=closed\">Geschlossen (" << closedOrders.size() << ")</a>";
    body << "</div>";
    const auto& selectedOrders = showClosed ? closedOrders : openOrders;
    if (selectedOrders.empty()) {
      body << "<div class=\"empty\">Keine " << (showClosed ? "geschlossenen" : "offenen") << " Aufträge vorhanden.</div>";
    } else {
      body << "<div class=\"list\">";
      for (const Order* order : selectedOrders) {
        body << "<a class=\"list-item\" href=\"/order/" << order->id << "\"><div><div class=\"list-title\">"
             << htmlEscape(order->title) << "</div><div class=\"list-meta\">Angelegt "
             << htmlEscape(displayDate(order->date));
        if (order->isClosed) body << " · abgeschlossen " << htmlEscape(displayDate(order->closedAt));
        body << "</div></div><span class=\"badge " << (order->isClosed ? "badge-closed" : "badge-open") << "\">"
             << (order->isClosed ? "Geschlossen" : "Offen") << "</span></a>";
      }
      body << "</div>";
    }
    body << "</section></div>";

    if (!attachedOrders.empty()) {
      body << "<section class=\"card\" style=\"margin-top:18px\"><div class=\"card-header\"><h2>Als Spender angehängt</h2></div><div class=\"list\">";
      for (const Order* order : attachedOrders) {
        const Vehicle* target = db_.findVehicle(order->vehicleId);
        body << "<a class=\"list-item\" href=\"/order/" << order->id << "\"><div><div class=\"list-title\">"
             << htmlEscape(order->title) << "</div><div class=\"list-meta\">Für "
             << htmlEscape(target ? vehicleDisplayName(*target) : "Unbekanntes Fahrzeug")
             << " · angelegt " << htmlEscape(displayDate(order->date));
        if (order->isClosed) body << " · abgeschlossen " << htmlEscape(displayDate(order->closedAt));
        body << "</div></div><span class=\"badge " << (order->isClosed ? "badge-closed" : "badge-open") << "\">"
             << (order->isClosed ? "Geschlossen" : "Offen") << "</span></a>";
      }
      body << "</div></section>";
    }

    return layout(request, session, &user, vehicleDisplayName(vehicle), body.str());
  }

  void detail(std::ostringstream& body, const std::string& label, const std::string& value) {
    body << "<div class=\"detail\"><span class=\"detail-label\">" << htmlEscape(label)
         << "</span><span class=\"detail-value\">" << htmlEscape(value.empty() ? "-" : value) << "</span></div>";
  }

  std::string addOrderPage(const Request& request, Session& session, const User& user, const Vehicle& vehicle) {
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Auftrag hinzufügen</h1><p>"
         << htmlEscape(vehicleDisplayName(vehicle)) << "</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"/vehicle/" << vehicle.id << "/add_order\">";
    body << "<div class=\"field\"><label for=\"title\">Titel</label><input id=\"title\" type=\"text\" name=\"title\" required></div>";
    body << "<div class=\"field\"><label for=\"description\">Beschreibung</label><textarea id=\"description\" name=\"description\"></textarea></div>";
    body << "<div class=\"field\"><label for=\"date\">Datum und Uhrzeit</label><input id=\"date\" type=\"datetime-local\" name=\"date\"></div>";
    body << "<div class=\"actions\"><button class=\"btn btn-primary\" type=\"submit\">Auftrag speichern</button>";
    body << "<a class=\"btn btn-secondary\" href=\"/vehicle/" << vehicle.id << "\">Abbrechen</a></div>";
    body << "</form></div>";
    return layout(request, session, &user, "Auftrag hinzufügen", body.str());
  }

  Response addOrderPost(const Request& request, Response response, Session& session, const Vehicle& vehicle) {
    Order order;
    order.id = db_.createOrderId();
    order.vehicleId = vehicle.id;
    order.title = trim(formValue(request.form, "title"));
    order.description = trim(formValue(request.form, "description"));
    order.date = formValue(request.form, "date");
    if (order.date.empty()) order.date = nowInput();
    db_.orders.push_back(order);
    db_.save();
    flash(session, "success", "Auftrag wurde angelegt.");
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  std::string orderPage(const Request& request, Session& session, const User& user, Order& order) {
    order.lastOpenedAt = nowInput();
    db_.save();

    const Vehicle* vehicle = db_.findVehicle(order.vehicleId);
    const auto totals = orderTotalsForUser(db_, user, order);
    const auto directTotals = directOrderTotals(db_, order);
    const auto costs = costsForOrder(db_, order.id);
    const auto times = timesForOrder(db_, order.id);
    const auto incomes = incomesForOrder(db_, order.id);
    const auto personUsers = selectableUsersForOrder(db_, order);
    const auto timeUsers = staffUsers(db_);

    std::ostringstream body;
    body << "<div class=\"page-header\"><div>";
    body << "<div style=\"margin-bottom:8px\"><span class=\"badge " << (order.isClosed ? "badge-closed" : "badge-open") << "\">"
         << (order.isClosed ? "Geschlossen" : "Offen") << "</span></div>";
    body << "<h1>" << htmlEscape(order.title) << "</h1><p>";
    if (vehicle) body << "<a href=\"/vehicle/" << vehicle->id << "\">" << htmlEscape(vehicleDisplayName(*vehicle)) << "</a>";
    body << " · angelegt " << htmlEscape(displayDate(order.date));
    if (order.isClosed) body << " · abgeschlossen " << htmlEscape(displayDate(order.closedAt));
    body << "</p></div><div class=\"actions\">";
    if (canModifyVehicles(user)) body << "<a class=\"btn btn-secondary\" href=\"/order/" << order.id << "/print\">PDF</a>";
    if (canModifyVehicles(user) && !order.isClosed) {
      body << "<a class=\"btn btn-secondary\" href=\"/order/" << order.id << "/edit\">Bearbeiten</a>";
      body << "<form method=\"post\" action=\"/order/" << order.id << "/close\" onsubmit=\"return confirm('Auftrag wirklich abschließen? Danach kann er nicht mehr bearbeitet werden.')\">";
      body << "<button class=\"btn btn-success\" type=\"submit\">Auftrag abschließen</button></form>";
    }
    body << "</div></div>";

    if (!order.description.empty()) {
      body << "<div class=\"card\" style=\"margin-bottom:20px\"><h2>Beschreibung</h2><p style=\"white-space:pre-wrap;margin-bottom:0\">"
           << htmlEscape(order.description) << "</p></div>";
    }
    if (order.isClosed) {
      body << "<div class=\"alert alert-info\">Dieser Auftrag ist abgeschlossen und schreibgeschützt. Ausgaben, Arbeitszeiten, Einnahmen und Auftragsdaten können nicht mehr geändert oder gelöscht werden.</div>";
    }

    attachedVehiclesSection(body, user, order);

    body << "<div class=\"grid\" style=\"margin-bottom:22px\">";
    stat(body, "Einnahmen", formatDecimal(totals.income) + " EUR", "span-3");
    stat(body, "EK", formatDecimal(totals.cost) + " EUR", "span-3");
    stat(body, "Ergebnis", formatDecimal(totals.result()) + " EUR", totals.result() >= 0 ? "span-3 positive" : "span-3 negative");
    stat(body, "Arbeitszeit", formatDecimal(totals.hours) + " h", "span-3");
    body << "</div>";

    if (canModifyVehicles(user) && !order.isClosed) {
      body << "<div class=\"grid\">";
      addCostForm(body, personUsers);
      addTimeForm(body, timeUsers);
      addIncomeForm(body, personUsers);
      body << "</div>";
    }

    costsTable(body, costs, user, order, directTotals);
    timesTable(body, times, user, order, directTotals);
    incomesTable(body, incomes, user, order, directTotals);
    return layout(request, session, &user, order.title, body.str());
  }

  void attachedVehiclesSection(std::ostringstream& body, const User& user, const Order& order) {
    std::vector<const Vehicle*> attached;
    for (int vehicleId : order.attachedVehicleIds) {
      if (const Vehicle* vehicle = db_.findVehicle(vehicleId)) {
        if (canAccessVehicle(db_, user, *vehicle)) {
          attached.push_back(vehicle);
        }
      }
    }
    std::sort(attached.begin(), attached.end(), [](const Vehicle* left, const Vehicle* right) {
      return toLower(vehicleDisplayName(*left)) < toLower(vehicleDisplayName(*right));
    });

    body << "<section class=\"card\" style=\"margin-bottom:22px\"><div class=\"card-header\"><h2>Angehängte Fahrzeuge</h2><strong>"
         << attached.size() << "</strong></div>";
    if (attached.empty()) {
      body << "<div class=\"empty\">Noch keine Fahrzeuge an diesen Auftrag angehängt.</div>";
    } else {
      body << "<div class=\"list\">";
      for (const Vehicle* vehicle : attached) {
        const Totals totals = ownVehicleTotals(db_, *vehicle);
        body << "<div class=\"list-item\"><div><div class=\"list-title\"><a href=\"/vehicle/" << vehicle->id << "\">"
             << htmlEscape(vehicleDisplayName(*vehicle)) << "</a></div>";
        body << "<div class=\"list-meta\">" << htmlEscape(vehicle->licensePlate.empty() ? "Kein Kennzeichen" : vehicle->licensePlate)
             << " · FIN/VIN: " << htmlEscape(vehicle->vin.empty() ? "-" : vehicle->vin)
             << " · EK " << formatDecimal(totals.cost) << " EUR"
             << " · Einnahmen " << formatDecimal(totals.income) << " EUR"
             << " · Arbeitszeit " << formatDecimal(totals.hours) << " h</div></div>";
        if (canModifyVehicles(user) && !order.isClosed) {
          body << "<form method=\"post\" action=\"/order/" << order.id << "/detach_vehicle/" << vehicle->id
               << "\" onsubmit=\"return confirm('Fahrzeug von diesem Auftrag lösen?')\">";
          body << "<button class=\"btn btn-secondary btn-sm\" type=\"submit\">Lösen</button></form>";
        }
        body << "</div>";
      }
      body << "</div>";
    }

    if (canModifyVehicles(user) && !order.isClosed) {
      std::vector<Vehicle*> attachable = visibleVehicles(db_, user);
      attachable.erase(std::remove_if(attachable.begin(), attachable.end(), [&order](const Vehicle* vehicle) {
                         return vehicle->id == order.vehicleId ||
                                std::find(order.attachedVehicleIds.begin(), order.attachedVehicleIds.end(), vehicle->id) !=
                                    order.attachedVehicleIds.end();
                       }),
                       attachable.end());
      if (!attachable.empty()) {
        body << "<form method=\"post\" action=\"/order/" << order.id << "\" class=\"grid\" style=\"margin-top:16px\">";
        body << "<div class=\"field span-8\"><label for=\"attached_vehicle_id\">Fahrzeug anhängen</label><select id=\"attached_vehicle_id\" name=\"attached_vehicle_id\" required>";
        for (const Vehicle* vehicle : attachable) {
          body << "<option value=\"" << vehicle->id << "\">" << htmlEscape(vehicleDisplayName(*vehicle))
               << " · " << htmlEscape(vehicle->licensePlate.empty() ? "Kein Kennzeichen" : vehicle->licensePlate)
               << " · FIN/VIN: " << htmlEscape(vehicle->vin.empty() ? "-" : vehicle->vin) << "</option>";
        }
        body << "</select></div><div class=\"field span-4\" style=\"align-self:end\">";
        body << "<button class=\"btn btn-primary\" type=\"submit\" name=\"attach_vehicle_submit\">Anhängen</button></div></form>";
      } else {
        body << "<p class=\"hint\">Keine weiteren Fahrzeuge zum Anhängen verfügbar.</p>";
      }
    }
    body << "</section>";
  }

  void addCostForm(std::ostringstream& body, const std::vector<User*>& users) {
    body << "<section class=\"card span-4\"><h2>Ausgabe hinzufügen</h2><form method=\"post\">";
    body << "<div class=\"field\"><label>Beschreibung</label><input type=\"text\" name=\"description\" required></div>";
    body << "<div class=\"field\"><label>EK (EUR)</label><input type=\"number\" step=\"0.01\" min=\"0\" name=\"amount\" required></div>";
    body << "<div class=\"field\"><label>VK (EUR)</label><input type=\"number\" step=\"0.01\" min=\"0\" name=\"saleAmount\" value=\"0\" required></div>";
    body << renderPersonSelect("cost_person", "Bezahlt von", "", "field", users);
    body << "<div class=\"field\"><label>Datum und Uhrzeit</label><input type=\"datetime-local\" name=\"date\"></div>";
    body << "<button class=\"btn btn-primary\" type=\"submit\" name=\"cost_submit\">Ausgabe speichern</button></form></section>";
  }

  void addTimeForm(std::ostringstream& body, const std::vector<User*>& users) {
    body << "<section class=\"card span-4\"><h2>Arbeitszeit hinzufügen</h2><form method=\"post\">";
    body << "<div class=\"field\"><label>Beschreibung</label><input type=\"text\" name=\"description\" required></div>";
    body << "<div class=\"field\"><label>Stunden</label><input type=\"number\" step=\"0.1\" min=\"0\" name=\"hours\" required></div>";
    body << renderPersonSelect("time_person", "Ausgeführt von", "", "field", users);
    body << "<div class=\"field\"><label>Datum und Uhrzeit</label><input type=\"datetime-local\" name=\"date\"></div>";
    body << "<button class=\"btn btn-primary\" type=\"submit\" name=\"time_submit\">Arbeitszeit speichern</button></form></section>";
  }

  void addIncomeForm(std::ostringstream& body, const std::vector<User*>& users) {
    body << "<section class=\"card span-4\"><h2>Einnahme hinzufügen</h2><form method=\"post\">";
    body << "<div class=\"field\"><label>Beschreibung</label><input type=\"text\" name=\"description\" required></div>";
    body << "<div class=\"field\"><label>Betrag (EUR)</label><input type=\"number\" step=\"0.01\" min=\"0\" name=\"amount\" required></div>";
    body << renderPersonSelect("income_person", "Erhalten von", "", "field", users);
    body << "<div class=\"field\"><label>Datum und Uhrzeit</label><input type=\"datetime-local\" name=\"date\"></div>";
    body << "<button class=\"btn btn-primary\" type=\"submit\" name=\"income_submit\">Einnahme speichern</button></form></section>";
  }

  void costsTable(std::ostringstream& body, const std::vector<Cost*>& costs, const User& user, const Order& order, const Totals& directTotals) {
    body << "<section class=\"card\" style=\"margin-top:22px\"><div class=\"card-header\"><h2>Ausgaben</h2><strong>EK "
         << formatDecimal(directTotals.cost) << " EUR</strong></div>";
    if (costs.empty()) {
      body << "<div class=\"empty\">Noch keine Ausgaben erfasst.</div></section>";
      return;
    }
    body << "<div class=\"table-wrap\"><table><thead><tr><th>Datum</th><th>Beschreibung</th><th>Person</th><th class=\"number\">EK</th><th class=\"number\">VK</th>";
    if (canModifyVehicles(user) && !order.isClosed) body << "<th></th>";
    body << "</tr></thead><tbody>";
    for (const Cost* cost : costs) {
      body << "<tr><td>" << htmlEscape(displayDate(cost->date)) << "</td><td>" << htmlEscape(cost->description)
           << "</td><td>" << htmlEscape(cost->person) << "</td><td class=\"number\">" << formatDecimal(cost->amount)
           << " EUR</td><td class=\"number\">" << formatDecimal(cost->saleAmount) << " EUR</td>";
      if (canModifyVehicles(user) && !order.isClosed) {
        body << "<td class=\"number\"><a class=\"btn btn-secondary btn-sm\" href=\"/edit_cost/" << cost->id << "\">Bearbeiten</a></td>";
      }
      body << "</tr>";
    }
    body << "</tbody></table></div></section>";
  }

  void timesTable(std::ostringstream& body, const std::vector<WorkTime*>& times, const User& user, const Order& order, const Totals& directTotals) {
    body << "<section class=\"card\"><div class=\"card-header\"><h2>Arbeitszeiten</h2><strong>"
         << formatDecimal(directTotals.hours) << " h</strong></div>";
    if (times.empty()) {
      body << "<div class=\"empty\">Noch keine Arbeitszeiten erfasst.</div></section>";
      return;
    }
    body << "<div class=\"table-wrap\"><table><thead><tr><th>Datum</th><th>Beschreibung</th><th>Person</th><th class=\"number\">Stunden</th>";
    if (canModifyVehicles(user) && !order.isClosed) body << "<th></th>";
    body << "</tr></thead><tbody>";
    for (const WorkTime* time : times) {
      body << "<tr><td>" << htmlEscape(displayDate(time->date)) << "</td><td>" << htmlEscape(time->description)
           << "</td><td>" << htmlEscape(time->person) << "</td><td class=\"number\">" << formatDecimal(time->hours)
           << " h</td>";
      if (canModifyVehicles(user) && !order.isClosed) {
        body << "<td class=\"number\"><a class=\"btn btn-secondary btn-sm\" href=\"/edit_time/" << time->id << "\">Bearbeiten</a></td>";
      }
      body << "</tr>";
    }
    body << "</tbody></table></div></section>";
  }

  void incomesTable(std::ostringstream& body, const std::vector<Income*>& incomes, const User& user, const Order& order, const Totals& directTotals) {
    body << "<section class=\"card\"><div class=\"card-header\"><h2>Einnahmen</h2><strong>"
         << formatDecimal(directTotals.income) << " EUR</strong></div>";
    if (incomes.empty()) {
      body << "<div class=\"empty\">Noch keine Einnahmen erfasst.</div></section>";
      return;
    }
    body << "<div class=\"table-wrap\"><table><thead><tr><th>Datum</th><th>Beschreibung</th><th>Person</th><th class=\"number\">Betrag</th>";
    if (canModifyVehicles(user) && !order.isClosed) body << "<th></th>";
    body << "</tr></thead><tbody>";
    for (const Income* income : incomes) {
      body << "<tr><td>" << htmlEscape(displayDate(income->date)) << "</td><td>" << htmlEscape(income->description)
           << "</td><td>" << htmlEscape(income->person) << "</td><td class=\"number\">" << formatDecimal(income->amount)
           << " EUR</td>";
      if (canModifyVehicles(user) && !order.isClosed) {
        body << "<td class=\"number\"><a class=\"btn btn-secondary btn-sm\" href=\"/edit_income/" << income->id << "\">Bearbeiten</a></td>";
      }
      body << "</tr>";
    }
    body << "</tbody></table></div></section>";
  }

  Response orderActionPost(const Request& request, Response response, Session& session, const User& user, Order& order) {
    if (!canModifyVehicles(user)) {
      return denied(response, session);
    }
    if (order.isClosed) {
      return closedOrder(response, session, order);
    }

    if (request.form.find("cost_submit") != request.form.end()) {
      Cost item;
      item.id = db_.createCostId();
      item.orderId = order.id;
      item.description = trim(formValue(request.form, "description"));
      item.amount = parseAmount(formValue(request.form, "amount"));
      item.saleAmount = parseAmount(formValue(request.form, "saleAmount"));
      item.person = trim(formValue(request.form, "person"));
      item.date = formValue(request.form, "date");
      if (item.date.empty()) item.date = nowInput();
      db_.costs.push_back(item);
      db_.save();
      flash(session, "success", "Ausgabe wurde gespeichert.");
    } else if (request.form.find("time_submit") != request.form.end()) {
      WorkTime item;
      item.id = db_.createTimeId();
      item.orderId = order.id;
      item.description = trim(formValue(request.form, "description"));
      item.hours = parseAmount(formValue(request.form, "hours"));
      item.person = trim(formValue(request.form, "person"));
      item.date = formValue(request.form, "date");
      if (item.date.empty()) item.date = nowInput();
      db_.times.push_back(item);
      db_.save();
      flash(session, "success", "Arbeitszeit wurde gespeichert.");
    } else if (request.form.find("income_submit") != request.form.end()) {
      Income item;
      item.id = db_.createIncomeId();
      item.orderId = order.id;
      item.description = trim(formValue(request.form, "description"));
      item.amount = parseAmount(formValue(request.form, "amount"));
      item.person = trim(formValue(request.form, "person"));
      item.date = formValue(request.form, "date");
      if (item.date.empty()) item.date = nowInput();
      db_.incomes.push_back(item);
      db_.save();
      flash(session, "success", "Einnahme wurde gespeichert.");
    } else if (request.form.find("attach_vehicle_submit") != request.form.end()) {
      const int vehicleId = parseInt(formValue(request.form, "attached_vehicle_id"));
      Vehicle* attachedVehicle = db_.findVehicle(vehicleId);
      if (!attachedVehicle) {
        flash(session, "danger", "Fahrzeug zum Anhängen wurde nicht gefunden.");
      } else if (!canAccessVehicle(db_, user, *attachedVehicle)) {
        return denied(response, session);
      } else if (vehicleId == order.vehicleId) {
        flash(session, "warning", "Das Hauptfahrzeug ist bereits mit diesem Auftrag verbunden.");
      } else if (std::find(order.attachedVehicleIds.begin(), order.attachedVehicleIds.end(), vehicleId) != order.attachedVehicleIds.end()) {
        flash(session, "info", "Dieses Fahrzeug ist bereits angehängt.");
      } else {
        order.attachedVehicleIds.push_back(vehicleId);
        db_.save();
        flash(session, "success", "Fahrzeug wurde an den Auftrag angehängt.");
      }
    } else {
      flash(session, "danger", "Unbekannte Aktion.");
    }
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  std::string editOrderPage(const Request& request, Session& session, const User& user, const Order& order) {
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Auftrag bearbeiten</h1><p>" << htmlEscape(order.title) << "</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"/order/" << order.id << "/edit\">";
    body << "<div class=\"field\"><label for=\"title\">Titel</label><input id=\"title\" type=\"text\" name=\"title\" value=\"" << htmlEscape(order.title) << "\" required></div>";
    body << "<div class=\"field\"><label for=\"description\">Beschreibung</label><textarea id=\"description\" name=\"description\">" << htmlEscape(order.description) << "</textarea></div>";
    body << "<div class=\"field\"><label for=\"date\">Datum und Uhrzeit</label><input id=\"date\" type=\"datetime-local\" name=\"date\" value=\"" << htmlEscape(order.date) << "\"></div>";
    body << "<div class=\"actions\"><button class=\"btn btn-primary\" type=\"submit\">Änderungen speichern</button>";
    body << "<a class=\"btn btn-secondary\" href=\"/order/" << order.id << "\">Abbrechen</a></div></form></div>";
    return layout(request, session, &user, "Auftrag bearbeiten", body.str());
  }

  Response editOrderPost(const Request& request, Response response, Session& session, Order& order) {
    order.title = trim(formValue(request.form, "title"));
    order.description = trim(formValue(request.form, "description"));
    order.date = formValue(request.form, "date");
    if (order.date.empty()) order.date = nowInput();
    db_.save();
    flash(session, "success", "Auftrag wurde gespeichert.");
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  Response closeOrderPost(Response response, Session& session, Order& order) {
    if (order.isClosed) {
      flash(session, "info", "Der Auftrag ist bereits abgeschlossen.");
    } else {
      order.isClosed = true;
      order.closedAt = nowInput();
      db_.save();
      flash(session, "success", "Auftrag abgeschlossen. Er ist ab jetzt schreibgeschützt.");
    }
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  Response detachVehiclePost(Response response, Session& session, Order& order, const Vehicle& vehicle) {
    if (order.isClosed) {
      return closedOrder(response, session, order);
    }
    const auto oldSize = order.attachedVehicleIds.size();
    order.attachedVehicleIds.erase(
        std::remove(order.attachedVehicleIds.begin(), order.attachedVehicleIds.end(), vehicle.id),
        order.attachedVehicleIds.end());
    if (order.attachedVehicleIds.size() != oldSize) {
      db_.save();
      flash(session, "success", "Fahrzeug wurde vom Auftrag gelöst.");
    } else {
      flash(session, "info", "Dieses Fahrzeug ist nicht an den Auftrag angehängt.");
    }
    return redirect(response, "/order/" + std::to_string(order.id));
  }

  std::string editCostPage(const Request& request, Session& session, const User& user, const Cost& cost) {
    const Order* order = db_.findOrder(cost.orderId);
    const auto personUsers = order ? selectableUsersForOrder(db_, *order) : sortedUsers(db_);
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Ausgabe bearbeiten</h1><p>" << htmlEscape(order ? order->title : "") << "</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"/edit_cost/" << cost.id << "\">";
    body << "<div class=\"field\"><label for=\"description\">Beschreibung</label><input id=\"description\" type=\"text\" name=\"description\" value=\"" << htmlEscape(cost.description) << "\" required></div>";
    body << "<div class=\"grid\"><div class=\"field span-6\"><label for=\"amount\">EK (EUR)</label><input id=\"amount\" type=\"number\" step=\"0.01\" min=\"0\" name=\"amount\" value=\"" << cost.amount << "\" required></div>";
    body << "<div class=\"field span-6\"><label for=\"saleAmount\">VK (EUR)</label><input id=\"saleAmount\" type=\"number\" step=\"0.01\" min=\"0\" name=\"saleAmount\" value=\"" << cost.saleAmount << "\" required></div>";
    body << renderPersonSelect("person", "Bezahlt von", cost.person, "field span-6", personUsers);
    body << "</div><div class=\"field\"><label for=\"date\">Datum und Uhrzeit</label><input id=\"date\" type=\"datetime-local\" name=\"date\" value=\"" << htmlEscape(cost.date) << "\"></div>";
    body << "<div class=\"actions\"><button class=\"btn btn-primary\" type=\"submit\">Änderungen speichern</button><a class=\"btn btn-secondary\" href=\"/order/" << cost.orderId << "\">Abbrechen</a></div></form></div>";
    body << "<div class=\"card\"><h2>Ausgabe löschen</h2><form method=\"post\" action=\"/delete_cost/" << cost.id << "\" onsubmit=\"return confirm('Diese Ausgabe endgültig löschen?')\"><button class=\"btn btn-danger\" type=\"submit\">Ausgabe löschen</button></form></div>";
    return layout(request, session, &user, "Ausgabe bearbeiten", body.str());
  }

  Response editCostPost(const Request& request, Response response, Session& session, Cost& cost) {
    cost.description = trim(formValue(request.form, "description"));
    cost.amount = parseAmount(formValue(request.form, "amount"));
    cost.saleAmount = parseAmount(formValue(request.form, "saleAmount"));
    cost.person = trim(formValue(request.form, "person"));
    cost.date = formValue(request.form, "date");
    if (cost.date.empty()) cost.date = nowInput();
    db_.save();
    flash(session, "success", "Ausgabe wurde gespeichert.");
    return redirect(response, "/order/" + std::to_string(cost.orderId));
  }

  std::string editTimePage(const Request& request, Session& session, const User& user, const WorkTime& time) {
    const Order* order = db_.findOrder(time.orderId);
    const auto users = staffUsers(db_);
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Arbeitszeit bearbeiten</h1><p>" << htmlEscape(order ? order->title : "") << "</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"/edit_time/" << time.id << "\">";
    body << "<div class=\"field\"><label for=\"description\">Beschreibung</label><input id=\"description\" type=\"text\" name=\"description\" value=\"" << htmlEscape(time.description) << "\" required></div>";
    body << "<div class=\"grid\"><div class=\"field span-6\"><label for=\"hours\">Stunden</label><input id=\"hours\" type=\"number\" step=\"0.1\" min=\"0\" name=\"hours\" value=\"" << time.hours << "\" required></div>";
    body << renderPersonSelect("person", "Ausgeführt von", time.person, "field span-6", users);
    body << "</div><div class=\"field\"><label for=\"date\">Datum und Uhrzeit</label><input id=\"date\" type=\"datetime-local\" name=\"date\" value=\"" << htmlEscape(time.date) << "\"></div>";
    body << "<div class=\"actions\"><button class=\"btn btn-primary\" type=\"submit\">Änderungen speichern</button><a class=\"btn btn-secondary\" href=\"/order/" << time.orderId << "\">Abbrechen</a></div></form></div>";
    body << "<div class=\"card\"><h2>Arbeitszeit löschen</h2><form method=\"post\" action=\"/delete_time/" << time.id << "\" onsubmit=\"return confirm('Diese Arbeitszeit endgültig löschen?')\"><button class=\"btn btn-danger\" type=\"submit\">Arbeitszeit löschen</button></form></div>";
    return layout(request, session, &user, "Arbeitszeit bearbeiten", body.str());
  }

  Response editTimePost(const Request& request, Response response, Session& session, WorkTime& time) {
    time.description = trim(formValue(request.form, "description"));
    time.hours = parseAmount(formValue(request.form, "hours"));
    time.person = trim(formValue(request.form, "person"));
    time.date = formValue(request.form, "date");
    if (time.date.empty()) time.date = nowInput();
    db_.save();
    flash(session, "success", "Arbeitszeit wurde gespeichert.");
    return redirect(response, "/order/" + std::to_string(time.orderId));
  }

  std::string editIncomePage(const Request& request, Session& session, const User& user, const Income& income) {
    const Order* order = db_.findOrder(income.orderId);
    const auto personUsers = order ? selectableUsersForOrder(db_, *order) : sortedUsers(db_);
    std::ostringstream body;
    body << "<div class=\"page-header\"><div><h1>Einnahme bearbeiten</h1><p>" << htmlEscape(order ? order->title : "") << "</p></div></div>";
    body << "<div class=\"card\"><form method=\"post\" action=\"/edit_income/" << income.id << "\">";
    body << "<div class=\"field\"><label for=\"description\">Beschreibung</label><input id=\"description\" type=\"text\" name=\"description\" value=\"" << htmlEscape(income.description) << "\" required></div>";
    body << "<div class=\"grid\"><div class=\"field span-6\"><label for=\"amount\">Betrag (EUR)</label><input id=\"amount\" type=\"number\" step=\"0.01\" min=\"0\" name=\"amount\" value=\"" << income.amount << "\" required></div>";
    body << renderPersonSelect("person", "Erhalten von", income.person, "field span-6", personUsers);
    body << "</div><div class=\"field\"><label for=\"date\">Datum und Uhrzeit</label><input id=\"date\" type=\"datetime-local\" name=\"date\" value=\"" << htmlEscape(income.date) << "\"></div>";
    body << "<div class=\"actions\"><button class=\"btn btn-primary\" type=\"submit\">Änderungen speichern</button><a class=\"btn btn-secondary\" href=\"/order/" << income.orderId << "\">Abbrechen</a></div></form></div>";
    body << "<div class=\"card\"><h2>Einnahme löschen</h2><form method=\"post\" action=\"/delete_income/" << income.id << "\" onsubmit=\"return confirm('Diese Einnahme endgültig löschen?')\"><button class=\"btn btn-danger\" type=\"submit\">Einnahme löschen</button></form></div>";
    return layout(request, session, &user, "Einnahme bearbeiten", body.str());
  }

  Response editIncomePost(const Request& request, Response response, Session& session, Income& income) {
    income.description = trim(formValue(request.form, "description"));
    income.amount = parseAmount(formValue(request.form, "amount"));
    income.person = trim(formValue(request.form, "person"));
    income.date = formValue(request.form, "date");
    if (income.date.empty()) income.date = nowInput();
    db_.save();
    flash(session, "success", "Einnahme wurde gespeichert.");
    return redirect(response, "/order/" + std::to_string(income.orderId));
  }

  Response deleteCostPost(Response response, Session& session, const User& user, const Cost& cost) {
    Order* order = db_.findOrder(cost.orderId);
    if (!order || !canModifyVehicles(user) || !canAccessOrder(db_, user, *order)) return denied(response, session);
    if (order->isClosed) return closedOrder(response, session, *order);
    const int orderId = cost.orderId;
    const int costId = cost.id;
    db_.costs.erase(std::remove_if(db_.costs.begin(), db_.costs.end(), [costId](const Cost& item) {
                      return item.id == costId;
                    }),
                    db_.costs.end());
    db_.save();
    flash(session, "success", "Ausgabe wurde gelöscht.");
    return redirect(response, "/order/" + std::to_string(orderId));
  }

  Response deleteTimePost(Response response, Session& session, const User& user, const WorkTime& time) {
    Order* order = db_.findOrder(time.orderId);
    if (!order || !canModifyVehicles(user) || !canAccessOrder(db_, user, *order)) return denied(response, session);
    if (order->isClosed) return closedOrder(response, session, *order);
    const int orderId = time.orderId;
    const int timeId = time.id;
    db_.times.erase(std::remove_if(db_.times.begin(), db_.times.end(), [timeId](const WorkTime& item) {
                     return item.id == timeId;
                   }),
                   db_.times.end());
    db_.save();
    flash(session, "success", "Arbeitszeit wurde gelöscht.");
    return redirect(response, "/order/" + std::to_string(orderId));
  }

  Response deleteIncomePost(Response response, Session& session, const User& user, const Income& income) {
    Order* order = db_.findOrder(income.orderId);
    if (!order || !canModifyVehicles(user) || !canAccessOrder(db_, user, *order)) return denied(response, session);
    if (order->isClosed) return closedOrder(response, session, *order);
    const int orderId = income.orderId;
    const int incomeId = income.id;
    db_.incomes.erase(std::remove_if(db_.incomes.begin(), db_.incomes.end(), [incomeId](const Income& item) {
                       return item.id == incomeId;
                     }),
                     db_.incomes.end());
    db_.save();
    flash(session, "success", "Einnahme wurde gelöscht.");
    return redirect(response, "/order/" + std::to_string(orderId));
  }

  Response vehiclePdf(Response response, const Vehicle& vehicle) {
    const Totals totals = vehicleTotals(db_, vehicle);
    std::vector<std::string> lines = {
        "Fahrzeug: " + vehicleDisplayName(vehicle),
        "Kennzeichen: " + (vehicle.licensePlate.empty() ? "-" : vehicle.licensePlate),
        "FIN/VIN: " + (vehicle.vin.empty() ? "-" : vehicle.vin),
        "Benutzer: " + userList(db_, vehicle.assignedUserIds),
        "Einnahmen: " + formatDecimal(totals.income) + " EUR",
        "EK: " + formatDecimal(totals.cost) + " EUR",
        "Ergebnis: " + formatDecimal(totals.result()) + " EUR",
        "Arbeitszeit: " + formatDecimal(totals.hours) + " h",
    };
    response.contentType = "application/pdf";
    response.headers["Content-Disposition"] = "inline; filename=\"fahrzeug.pdf\"";
    response.body = buildSimplePdf("Fahrzeugbericht", lines);
    return response;
  }

  Response orderPdf(Response response, const Order& order) {
    const Vehicle* vehicle = db_.findVehicle(order.vehicleId);
    const Totals totals = orderTotals(db_, order);
    std::vector<std::string> lines = {
        "Auftrag: " + order.title,
        "Fahrzeug: " + (vehicle ? vehicleDisplayName(*vehicle) : "-"),
        "Angelegt: " + displayDate(order.date),
        "Status: " + std::string(order.isClosed ? "Geschlossen" : "Offen"),
        "Einnahmen: " + formatDecimal(totals.income) + " EUR",
        "EK: " + formatDecimal(totals.cost) + " EUR",
        "Ergebnis: " + formatDecimal(totals.result()) + " EUR",
        "Arbeitszeit: " + formatDecimal(totals.hours) + " h",
    };
    response.contentType = "application/pdf";
    response.headers["Content-Disposition"] = "inline; filename=\"auftrag.pdf\"";
    response.body = buildSimplePdf("Auftragsbericht", lines);
    return response;
  }

  Database db_;
  std::unordered_map<std::string, Session> sessions_;
};

std::map<std::string, std::string> parseCookies(const std::string& header) {
  std::map<std::string, std::string> cookies;
  std::size_t start = 0;
  while (start < header.size()) {
    const auto end = header.find(';', start);
    const auto part = trim(header.substr(start, end == std::string::npos ? std::string::npos : end - start));
    const auto equals = part.find('=');
    if (equals != std::string::npos) {
      cookies[trim(part.substr(0, equals))] = trim(part.substr(equals + 1));
    }
    if (end == std::string::npos) break;
    start = end + 1;
  }
  return cookies;
}

Request parseRequest(const std::string& raw) {
  Request request;
  const auto headerEnd = raw.find("\r\n\r\n");
  const auto headerPart = raw.substr(0, headerEnd);
  request.body = headerEnd == std::string::npos ? "" : raw.substr(headerEnd + 4);

  std::istringstream input(headerPart);
  std::string line;
  if (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    std::istringstream requestLine(line);
    std::string target;
    requestLine >> request.method >> target;
    const auto queryPos = target.find('?');
    request.path = queryPos == std::string::npos ? target : target.substr(0, queryPos);
    request.query = queryPos == std::string::npos ? "" : target.substr(queryPos + 1);
    request.queryValues = parseKeyValues(request.query);
  }
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    const auto colon = line.find(':');
    if (colon == std::string::npos) continue;
    request.headers[toLower(trim(line.substr(0, colon)))] = trim(line.substr(colon + 1));
  }
  const auto cookieHeader = request.headers.find("cookie");
  if (cookieHeader != request.headers.end()) {
    request.cookies = parseCookies(cookieHeader->second);
  }
  const auto contentType = request.headers.find("content-type");
  if (contentType != request.headers.end() && startsWith(toLower(contentType->second), "application/x-www-form-urlencoded")) {
    request.form = parseKeyValues(request.body);
  }
  return request;
}

std::string receiveAll(SOCKET client) {
  std::string data;
  char buffer[4096];
  while (data.find("\r\n\r\n") == std::string::npos) {
    const int received = recv(client, buffer, sizeof(buffer), 0);
    if (received <= 0) return data;
    data.append(buffer, buffer + received);
    if (data.size() > 1024 * 1024) return data;
  }
  const auto request = parseRequest(data);
  int contentLength = 0;
  const auto found = request.headers.find("content-length");
  if (found != request.headers.end()) {
    contentLength = parseInt(found->second);
  }
  const auto headerEnd = data.find("\r\n\r\n");
  while (contentLength > 0 && data.size() < headerEnd + 4 + static_cast<std::size_t>(contentLength)) {
    const int received = recv(client, buffer, sizeof(buffer), 0);
    if (received <= 0) break;
    data.append(buffer, buffer + received);
    if (data.size() > 1024 * 1024) break;
  }
  return data;
}

std::string statusLine(const Response& response) {
  return "HTTP/1.1 " + std::to_string(response.status) + " " + response.statusText + "\r\n";
}

std::string serializeResponse(const Response& response) {
  std::ostringstream output;
  output << statusLine(response);
  output << "Content-Type: " << response.contentType << "\r\n";
  output << "Content-Length: " << response.body.size() << "\r\n";
  output << "Connection: close\r\n";
  for (const auto& [key, value] : response.headers) {
    output << key << ": " << value << "\r\n";
  }
  output << "\r\n";
  output << response.body;
  return output.str();
}

class HttpServer {
public:
  HttpServer(int port, std::function<Response(Request)> handler)
      : port_(port), handler_(std::move(handler)) {}

  int run() {
    WSADATA data{};
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0) {
      std::cerr << "WSAStartup fehlgeschlagen.\n";
      return 1;
    }

    SOCKET server = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server == INVALID_SOCKET) {
      std::cerr << "Socket konnte nicht erstellt werden.\n";
      WSACleanup();
      return 1;
    }

    BOOL reuse = TRUE;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&reuse), sizeof(reuse));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    address.sin_port = htons(static_cast<u_short>(port_));

    if (bind(server, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == SOCKET_ERROR) {
      std::cerr << "Port " << port_ << " konnte nicht gebunden werden.\n";
      closesocket(server);
      WSACleanup();
      return 1;
    }

    if (listen(server, SOMAXCONN) == SOCKET_ERROR) {
      std::cerr << "Listen fehlgeschlagen.\n";
      closesocket(server);
      WSACleanup();
      return 1;
    }

    std::cout << "Vehicle Manager C++ läuft auf http://127.0.0.1:" << port_ << "\n";
    std::cout << "Zum Beenden dieses Fenster schließen oder Strg+C drücken.\n";

    while (true) {
      SOCKET client = accept(server, nullptr, nullptr);
      if (client == INVALID_SOCKET) {
        continue;
      }
      const auto raw = receiveAll(client);
      Response response;
      if (raw.empty()) {
        response.status = 400;
        response.statusText = "Bad Request";
        response.body = "Bad Request";
        response.contentType = "text/plain; charset=utf-8";
      } else {
        response = handler_(parseRequest(raw));
      }
      const auto serialized = serializeResponse(response);
      send(client, serialized.data(), static_cast<int>(serialized.size()), 0);
      shutdown(client, SD_SEND);
      closesocket(client);
    }

    closesocket(server);
    WSACleanup();
    return 0;
  }

private:
  int port_;
  std::function<Response(Request)> handler_;
};

int portFromEnvironment() {
  char* rawPort = nullptr;
  std::size_t valueSize = 0;
  if (_dupenv_s(&rawPort, &valueSize, "VEHICLE_MANAGER_CPP_PORT") == 0 && rawPort != nullptr) {
    const int port = parseInt(rawPort);
    std::free(rawPort);
    if (port > 0 && port < 65536) {
      return port;
    }
  }
  return 8080;
}

}  // namespace cppvm

int main() {
  const auto databasePath = std::filesystem::current_path() / "werkstatt_cpp.db";
  cppvm::Database database(databasePath);
  database.load();
  database.ensureDefaultAdmin();

  std::cout << "C++ DB: " << databasePath.string() << "\n";
  std::cout << "Default-Login bei neuer DB: admin@example.com / admin\n";

  cppvm::Application app(std::move(database));
  cppvm::HttpServer server(cppvm::portFromEnvironment(), [&app](cppvm::Request request) {
    return app.handle(std::move(request));
  });
  return server.run();
}
