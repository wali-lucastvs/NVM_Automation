/*
 * NvM_Cfg.h
 * Auto-generated NvM configuration header.
 * Integrate the generated types with your platform Std_Types.h if needed.
 */

#ifndef NVM_CFG_H
#define NVM_CFG_H

#include "Std_Types.h"
#include <stdint.h> /* For uint8_t, uint16_t */
#include <stdbool.h> /* For bool, true, false */

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
    uint16_t BlockId;
    uint16_t BlockLength;
    uint8_t* RamBlockDataAddress;
    NvM_DeviceType DeviceId;
    NvM_BlockManagementTypeType BlockManagementType;
    bool BlockUseCrc;
    NvM_CrcType BlockCrcType;
    bool WriteProtection;
} NvM_BlockDescriptorType;

/* Number of merged NvM blocks. */
#define NVM_NUMBER_OF_BLOCKS (5u)

/* Symbolic block identifiers. */
#define NVM_BLOCK_ID_WALI (2u)
#define NVM_BLOCK_ID_HAIDER (3u)
#define NVM_BLOCK_ID_ZAIDI (4u)
#define NVM_BLOCK_ID_WALI_BLOCK (10u)
#define NVM_BLOCK_ID_ENGINE_SETTINGS (20u)

extern const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS];

#ifdef __cplusplus
}
#endif

#endif /* NVM_CFG_H */
