import { useState } from 'react'
import { TabCustomiser } from './TabCustomiser'
import { Tabs } from './Tabs'
import type { useCustomisableTabs } from '../hooks/useCustomisableTabs'

type TabsState<T extends string> = ReturnType<typeof useCustomisableTabs<T>>

/**
 * A page's primary tab row, in this user's own order, with the reorder panel attached.
 *
 * Pages pair this with `useCustomisableTabs`, which owns the state (so the page can still read
 * `tab` for its own rendering) while this component owns the presentation. Splitting it that way
 * keeps every tabbed page down to two lines and one shared behaviour, rather than each page
 * re-implementing ordering, the trigger and the panel.
 */
export function CustomisableTabs<T extends string>({
  state,
  label,
  mobileSelectLabel,
  className,
}: {
  state: TabsState<T>
  /** Names the page in the reorder panel's title, e.g. "Money". */
  label: string
  mobileSelectLabel?: string
  className?: string
}) {
  const [customising, setCustomising] = useState(false)
  return (
    <>
      <Tabs
        tabs={state.orderedTabs}
        active={state.tab}
        onChange={state.setTab}
        mobileSelectLabel={mobileSelectLabel}
        className={className}
        onCustomise={() => setCustomising(true)}
      />
      {customising && (
        <TabCustomiser
          title={`Reorder ${label} tabs`}
          tabs={state.orderedTabs}
          isCustomised={state.isCustomised}
          onSave={state.saveOrder}
          onReset={state.resetOrder}
          onClose={() => setCustomising(false)}
        />
      )}
    </>
  )
}
