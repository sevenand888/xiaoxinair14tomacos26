// Host-only tests of the exact image gate; never loads or patches a kext.
#include "../Sources/SHDAHDAUIdentity.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include <cstdlib>
using namespace shda::hdauDiagnostic;
static unsigned checks;
void require(bool condition, const char *name) {
    ++checks;
    if (!condition) { std::cerr << "FAIL: " << name << '\n'; std::exit(1); }
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<uint8_t> original((std::istreambuf_iterator<char>(input)), {});
    require(original.size() == 1880752, "archived target file size");
    require(!checkImage(original.data(), original.size()), "exact target image accepted");
    require(!checkProbe(reinterpret_cast<uintptr_t>(original.data()), original.size(),
        reinterpret_cast<uintptr_t>(original.data() + 0x11ae0)), "exact target probe accepted");
    require(checkImage(nullptr, 0), "null rejected");
    require(checkImage(original.data(), 31), "short header rejected");
    auto changed = original;
    auto h = reinterpret_cast<mach_header_64 *>(changed.data());
    h->magic = 0;
    require(checkImage(changed.data(), changed.size()), "wrong magic rejected");
    changed = original; h = reinterpret_cast<mach_header_64 *>(changed.data());
    h->cputype = CPU_TYPE_ARM64;
    require(checkImage(changed.data(), changed.size()), "wrong CPU rejected");
    changed = original; h = reinterpret_cast<mach_header_64 *>(changed.data());
    h->sizeofcmds = UINT32_MAX;
    require(checkImage(changed.data(), changed.size()), "oversized commands rejected");
    changed = original; h = reinterpret_cast<mach_header_64 *>(changed.data());
    h->ncmds = UINT32_MAX;
    require(checkImage(changed.data(), changed.size()), "oversized command count rejected");
    changed = original;
    reinterpret_cast<load_command *>(changed.data() + sizeof(*h))->cmdsize = 0;
    require(checkImage(changed.data(), changed.size()), "zero command length rejected");
    changed = original; h = reinterpret_cast<mach_header_64 *>(changed.data());
    auto c = reinterpret_cast<load_command *>(h + 1);
    bool uuidFound = false;
    for (uint32_t i = 0; i < h->ncmds; ++i) {
        if (c->cmd == LC_UUID) {
            auto u = reinterpret_cast<uuid_command *>(c);
            u->uuid[0] ^= 1;
            require(checkImage(changed.data(), changed.size()), "unknown UUID rejected");
            u->uuid[0] ^= 1;
            c->cmd = 0;
            require(checkImage(changed.data(), changed.size()), "missing UUID rejected");
            uuidFound = true; break;
        }
        c = reinterpret_cast<load_command *>(reinterpret_cast<uint8_t *>(c) + c->cmdsize);
    }
    require(uuidFound, "target UUID command exists");
    changed = original;
    auto base = reinterpret_cast<uintptr_t>(changed.data());
    require(checkProbe(base, changed.size(), 0), "zero probe rejected");
    require(checkProbe(base, changed.size(), base - 1), "probe below image rejected");
    require(checkProbe(base, changed.size(), base + changed.size()), "probe after image rejected");
    require(checkProbe(base, changed.size(), base + changed.size() - sizeof(expectedProbe) + 1),
        "truncated probe rejected");
    changed[0x11ae0] ^= 1;
    require(checkProbe(base, changed.size(), base + 0x11ae0), "already modified probe rejected");
    std::cout << "PASS " << checks << " image/probe guard checks\n";
}
