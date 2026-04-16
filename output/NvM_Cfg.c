/*
 * NvM_Cfg.c
 * Auto-generated NvM configuration source.
 */

#include "NvM_Cfg.h"

/* External RAM block buffers configured for permanent RAM usage. */
extern uint8 Ram_EngineSettings[64u];
extern uint8 Ram_OdometerMirror[16u];
extern uint8 Ram_DiagnosticSnapshot[128u];

/*
 * NvM block descriptor table.
 * Each entry maps one logical NvM block to its RAM block and storage attributes.
 */
const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS] =
{
    /* EngineSettings: block ID 2, FEE, NATIVE, CRC16 */
    {
        .BlockId = NVM_BLOCK_ID_ENGINE_SETTINGS,
        .BlockLength = 64u,
        .RamBlockDataAddress = Ram_EngineSettings,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_NATIVE,
        .BlockUseCrc = TRUE,
        .BlockCrcType = NVM_CRC16,
        .WriteProtection = FALSE
    },
    /* OdometerMirror: block ID 3, EA, REDUNDANT, CRC32 */
    {
        .BlockId = NVM_BLOCK_ID_ODOMETER_MIRROR,
        .BlockLength = 16u,
        .RamBlockDataAddress = Ram_OdometerMirror,
        .DeviceId = NVM_DEVICE_EA,
        .BlockManagementType = NVM_BLOCK_REDUNDANT,
        .BlockUseCrc = TRUE,
        .BlockCrcType = NVM_CRC32,
        .WriteProtection = TRUE
    },
    /* DiagnosticSnapshot: block ID 4, FEE, DATASET, NO_CRC */
    {
        .BlockId = NVM_BLOCK_ID_DIAGNOSTIC_SNAPSHOT,
        .BlockLength = 128u,
        .RamBlockDataAddress = Ram_DiagnosticSnapshot,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_DATASET,
        .BlockUseCrc = FALSE,
        .BlockCrcType = NVM_CRC_NONE,
        .WriteProtection = FALSE
    }
};
