/*
 * NvM_Cfg.c
 * Auto-generated NvM configuration source.
 */

#include "NvM_Cfg.h"

/* External RAM block buffers configured for permanent RAM usage. */
extern uint8_t Ram_OdometerMirror[16u];
extern uint8_t Ram_DiagnosticSnapshot[128u];
extern uint8_t Ram_LegacyBlock[8u];
extern uint8_t Ram_EngineSettings[64u];

/*
 * Merged NvM block descriptor table.
 * Existing blocks from the previous ARXML are preserved and new blocks are appended.
 */
const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS] =
{
    /* OdometerMirror: block ID 3, EA, REDUNDANT, CRC32 */
    {
        .BlockId = NVM_BLOCK_ID_ODOMETER_MIRROR,
        .BlockLength = 16u,
        .RamBlockDataAddress = Ram_OdometerMirror,
        .DeviceId = NVM_DEVICE_EA,
        .BlockManagementType = NVM_BLOCK_REDUNDANT,
        .BlockUseCrc = true,
        .BlockCrcType = NVM_CRC32,
        .WriteProtection = true
    },
    /* DiagnosticSnapshot: block ID 4, FEE, DATASET, NO_CRC */
    {
        .BlockId = NVM_BLOCK_ID_DIAGNOSTIC_SNAPSHOT,
        .BlockLength = 128u,
        .RamBlockDataAddress = Ram_DiagnosticSnapshot,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_DATASET,
        .BlockUseCrc = false,
        .BlockCrcType = NVM_CRC_NONE,
        .WriteProtection = false
    },
    /* WaliBlock: block ID 10, FEE, NATIVE, CRC16 */
    {
        .BlockId = NVM_BLOCK_ID_WALI_BLOCK,
        .BlockLength = 8u,
        .RamBlockDataAddress = Ram_LegacyBlock,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_NATIVE,
        .BlockUseCrc = true,
        .BlockCrcType = NVM_CRC16,
        .WriteProtection = false
    },
    /* EngineSettings: block ID 20, FEE, NATIVE, CRC16 */
    {
        .BlockId = NVM_BLOCK_ID_ENGINE_SETTINGS,
        .BlockLength = 64u,
        .RamBlockDataAddress = Ram_EngineSettings,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_NATIVE,
        .BlockUseCrc = true,
        .BlockCrcType = NVM_CRC16,
        .WriteProtection = false
    }
};
