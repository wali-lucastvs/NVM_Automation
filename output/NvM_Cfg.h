/*
 * NvM_Cfg.h
 * Auto-generated NvM configuration header.
 * Integrate the generated types with your platform Std_Types.h if needed.
 */

#ifndef NVM_CFG_H
#define NVM_CFG_H

#include "Std_Types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum
{
    NVM_DEVICE_FEE = 0,
    NVM_DEVICE_EA = 1
} NvM_DeviceType;

typedef enum
{
    NVM_BLOCK_NATIVE = 0,
    NVM_BLOCK_REDUNDANT = 1,
    NVM_BLOCK_DATASET = 2
} NvM_BlockManagementTypeType;

typedef enum
{
    NVM_CRC_NONE = 0,
    NVM_CRC8 = 1,
    NVM_CRC16 = 2,
    NVM_CRC32 = 3
} NvM_CrcType;

typedef struct
{
    uint16 BlockId;
    uint16 BlockLength;
    uint8* RamBlockDataAddress;
    NvM_DeviceType DeviceId;
    NvM_BlockManagementTypeType BlockManagementType;
    boolean BlockUseCrc;
    NvM_CrcType BlockCrcType;
    boolean WriteProtection;
} NvM_BlockDescriptorType;

/* Number of generated NvM blocks. */
#define NVM_NUMBER_OF_BLOCKS (3u)

/* Symbolic block identifiers. */
#define NVM_BLOCK_ID_ENGINE_SETTINGS (2u)
#define NVM_BLOCK_ID_ODOMETER_MIRROR (3u)
#define NVM_BLOCK_ID_DIAGNOSTIC_SNAPSHOT (4u)

extern const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS];

#ifdef __cplusplus
}
#endif

#endif /* NVM_CFG_H */
