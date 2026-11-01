// Diagnostic guard for the archived HDAUniversal 1.0.46 image only.
// Archive SHA256: e4d49303de9db4a2022a569da97260b55926c13bdabf38ce8b7083caa925d7ed
// Runtime relocation prevents comparing the entire file hash. Require its UUID
// and the relocation-free probe prologue before permitting a Lilu route.
#pragma once
#include <mach-o/loader.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

namespace shda { namespace hdauDiagnostic {
constexpr uint8_t expectedUUID[] = {
    0x82, 0x59, 0x0b, 0x0e, 0x68, 0xe9, 0x30, 0xb0,
    0xa8, 0x24, 0xb3, 0xd5, 0x1f, 0xd4, 0x89, 0x0e
};
constexpr uint8_t expectedProbe[] = {
    0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56,
    0x41, 0x55, 0x41, 0x54, 0x53, 0x48, 0x83, 0xec,
    0x58, 0x49, 0x89, 0xd6, 0x49, 0x89, 0xf7, 0x49,
    0x89, 0xfd
};
inline const char *checkImage(const void *image, size_t size) {
    if (!image || size < sizeof(mach_header_64)) return "invalid-image-range";
    auto header = static_cast<const mach_header_64 *>(image);
    if (header->magic != MH_MAGIC_64 || header->cputype != CPU_TYPE_X86_64)
        return "invalid-image-header";
    if (header->sizeofcmds > size - sizeof(*header) || header->sizeofcmds > 0x10000 ||
        header->ncmds > header->sizeofcmds / sizeof(load_command))
        return "invalid-load-commands";
    const auto commands = reinterpret_cast<const uint8_t *>(header + 1);
    size_t offset = 0;
    bool found = false;
    for (uint32_t i = 0; i < header->ncmds; ++i) {
        if (offset > header->sizeofcmds || header->sizeofcmds - offset < sizeof(load_command))
            return "truncated-load-command";
        auto command = reinterpret_cast<const load_command *>(commands + offset);
        if (command->cmdsize < sizeof(load_command) || command->cmdsize > header->sizeofcmds - offset)
            return "invalid-load-command-size";
        if (command->cmd == LC_UUID) {
            if (found || command->cmdsize != sizeof(uuid_command)) return "invalid-uuid-command";
            auto uuid = reinterpret_cast<const uuid_command *>(command);
            if (memcmp(uuid->uuid, expectedUUID, sizeof(expectedUUID))) return "unsupported-hdau-uuid";
            found = true;
        }
        offset += command->cmdsize;
    }
    if (offset != header->sizeofcmds) return "inconsistent-load-commands";
    return found ? nullptr : "missing-hdau-uuid";
}
inline const char *checkProbe(uintptr_t base, size_t size, uintptr_t probe) {
    if (!probe || probe < base || probe - base > size || sizeof(expectedProbe) > size - (probe - base))
        return "probe-outside-image";
    return memcmp(reinterpret_cast<const void *>(probe), expectedProbe, sizeof(expectedProbe))
        ? "unsupported-probe-prologue" : nullptr;
}
} }
