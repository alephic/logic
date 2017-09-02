#include "logic.h"
#include "parse.h"
#include <sstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  std::string lineStr;
  while (true) {
    std::cout << '>' << ' ';
    std::getline(std::cin, lineStr);
    if (lineStr == ":q") {
      return 0;
    }
    std::stringstream lineStream(lineStr);
    logic::ValPtr expr = parse::parse(lineStream);
    if (expr) {
      expr->repr(std::cout);
      std::cout << std::endl;
    } else {
      std::cout << "Syntax error" << std::endl;
    }
  }
}