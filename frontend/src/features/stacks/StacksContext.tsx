import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../../api/client'
import type { Household, NodeInfo } from '../../api/types'

interface StacksCtx {
  nodes: NodeInfo[]
  enabledKeys: Set<string>
  household: Household | null
  loading: boolean
  refresh: () => Promise<void>
}

const Ctx = createContext<StacksCtx>({
  nodes: [], enabledKeys: new Set(), household: null, loading: true, refresh: async () => {},
})

export function StacksProvider({ children }: { children: ReactNode }) {
  const [nodes, setNodes] = useState<NodeInfo[]>([])
  const [household, setHousehold] = useState<Household | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const [n, h] = await Promise.all([
      api.getNodes().catch(() => [] as NodeInfo[]),
      api.getHousehold().catch(() => null),
    ])
    setNodes(n)
    setHousehold(h)
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const enabledKeys = new Set(nodes.filter(n => n.is_enabled && !n.is_hidden).map(n => n.key))

  return (
    <Ctx.Provider value={{ nodes, enabledKeys, household, loading, refresh }}>
      {children}
    </Ctx.Provider>
  )
}

export const useStacks = () => useContext(Ctx)
