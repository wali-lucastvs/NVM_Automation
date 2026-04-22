/*
 * NvM_Cfg.c
 * Auto-generated NvM configuration source.
 */

#include "NvM_Cfg.h"

/* External RAM block buffers configured for permanent RAM usage. */
extern uint8_t Ram_NewBlock[16u];
extern uint8_t Ram_LegacyBlock[8u];

/*
 * Merged NvM block descriptor table.
 * Existing blocks from the previous ARXML are preserved and new blocks are appended.
 */
const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS] =
{
    /* NewBlock: block ID 5, FEE, NATIVE, CRC16 */
    {
        .BlockId = NVM_BLOCK_ID_NEW_BLOCK,
        .BlockLength = 16u,
        .RamBlockDataAddress = Ram_NewBlock,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_NATIVE,
        .BlockUseCrc = true,
        .BlockCrcType = NVM_CRC16,
        .WriteProtection = false
    },
    /* LegacyBlock: block ID 10, FEE, NATIVE, CRC16 */
    {
        .BlockId = NVM_BLOCK_ID_LEGACY_BLOCK,
        .BlockLength = 8u,
        .RamBlockDataAddress = Ram_LegacyBlock,
        .DeviceId = NVM_DEVICE_FEE,
        .BlockManagementType = NVM_BLOCK_NATIVE,
        .BlockUseCrc = true,
        .BlockCrcType = NVM_CRC16,
        .WriteProtection = false
    }
};
