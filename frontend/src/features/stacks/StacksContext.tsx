import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../../api/client'
import type { Household, NodeInfo } from '../../api/types'

interface StacksCtx {
  nodes: NodeInfo[]
  enabledKeys: Set<string>
  household: Household | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

const Ctx = createContext<StacksCtx>({
  nodes: [], enabledKeys: new Set(), household: null, loading: true, error: null, refresh: async () => {},
})

export function StacksProvider({ children }: { children: ReactNode }) {
  const [nodes, setNodes] = useState<NodeInfo[]>([])
  const [household, setHousehold] = useState<Household | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setError(null)
    const [nodesResult, householdResult] = await Promise.allSettled([
      api.getNodes(),
      api.getHousehold(),
    ])
    if (nodesResult.status === 'fulfilled') setNodes(nodesResult.value)
    if (householdResult.status === 'fulfilled') setHousehold(householdResult.value)
    if (nodesResult.status === 'rejected' || householdResult.status === 'rejected') {
      setError('Some household settings could not be loaded.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const enabledKeys = new Set(nodes.filter(n => n.is_enabled && !n.is_hidden).map(n => n.key))

  return (
    <Ctx.Provider value={{ nodes, enabledKeys, household, loading, error, refresh }}>
      {children}
    </Ctx.Provider>
  )
}

export const useStacks = () => useContext(Ctx)
