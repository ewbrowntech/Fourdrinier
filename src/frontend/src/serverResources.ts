const BYTES_PER_GIBIBYTE = 1024 ** 3

export interface ServerResourceValues {
  cpuCores: number
  memoryGib: number
}

export const DEFAULT_SERVER_RESOURCES: ServerResourceValues = {
  cpuCores: 1,
  memoryGib: 2,
}

const RUNTIME_MINIMUM_RESOURCES: Record<'pumpkin', ServerResourceValues> = {
  pumpkin: {
    cpuCores: 2,
    memoryGib: 2,
  },
}

export function minimumResourcesForRuntime(runtime: 'pumpkin'): ServerResourceValues {
  return RUNTIME_MINIMUM_RESOURCES[runtime]
}

export function coresToMillicores(cores: number): number {
  return Math.round(cores * 1000)
}

export function gibibytesToBytes(gibibytes: number): number {
  return Math.round(gibibytes * BYTES_PER_GIBIBYTE)
}

export function millicoresToCores(millicores: number): number {
  return millicores / 1000
}

export function bytesToGibibytes(bytes: number): number {
  return bytes / BYTES_PER_GIBIBYTE
}

export function formatCpu(millicores: number): string {
  const cores = millicoresToCores(millicores)
  return `${cores.toLocaleString(undefined, { maximumFractionDigits: 3 })} CPU`
}

export function formatMemory(bytes: number): string {
  const gibibytes = bytesToGibibytes(bytes)
  return `${gibibytes.toLocaleString(undefined, { maximumFractionDigits: 3 })} GiB`
}
