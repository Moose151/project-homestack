import { STACKS, type StackDef } from './stacks'

export interface NodeGuide {
  key: string
  label: string
  icon: string
  colour: string
  summary: string
  purpose: string
  gettingStarted: string[]
  capabilities: string[]
  connections: string[]
}

const details: Record<string, Pick<NodeGuide, 'purpose' | 'gettingStarted' | 'capabilities' | 'connections'>> = {
  hub: {
    purpose: 'A personal start page that brings the household information needing attention together.',
    gettingStarted: ['Choose the widgets you want to see.', 'Use the due, countdown and activity cards to jump to their source.'],
    capabilities: ['Personal widget layout', 'Upcoming work and household activity', 'Timed countdowns and quick actions'],
    connections: ['Receives due work and events from Calendar, Lists & Notes and enabled nodes.', 'Links back to the exact source record where possible.'],
  },
  corners: {
    purpose: 'A person-centred view of assignments, wishes and recent activity across HomeStack.',
    gettingStarted: ['Open My Corner to see your own page.', 'Choose another household member to see what they have shared.'],
    capabilities: ['Assigned work', 'Personal and shared wish lists', 'Activity reactions and source links'],
    connections: ['Fitness activity can be expanded in place.', 'Lists & Notes items, Tasks work and other activity link to their source.'],
  },
  calendar: {
    purpose: 'The shared timeline for events, appointments and dated work.',
    gettingStarted: ['Add an event or appointment.', 'Assign people and choose whether it is private or shared.'],
    capabilities: ['Month and agenda views', 'Events and appointments', 'Node-owned schedule entries'],
    connections: ['Lists & Notes shows the same agenda.', 'Enabled nodes publish dates without duplicating their source record.'],
  },
  atlas: {
    purpose: 'Shared lists, to-dos, notes, reminders, contacts and a practical daily agenda.',
    gettingStarted: ['Create a list for a purpose such as groceries or to-dos.', 'Assign dated items so they appear in Agenda and Calendar.'],
    capabilities: ['Lists and reusable notes', 'Due dates and assignees', 'Appointments and events with filters'],
    connections: ['Dated items flow to Calendar and Dashboard.', 'Agenda edits Lists & Notes items and standalone events without leaving Lists & Notes.'],
  },
  education: {
    purpose: 'Study planning for institutions, courses, classes, assessments and results.',
    gettingStarted: ['Add the institution first.', 'Create a study profile and select that saved institution.'],
    capabilities: ['Per-person study profiles', 'Courses and assessments', 'Classes, events and results'],
    connections: ['Deadlines and classes publish to Calendar.', 'The signed-in person is selected by default.'],
  },
  books: {
    purpose: 'Keep reading lists, book clubs, progress and book wish lists together.',
    gettingStarted: ['Add a book or reading goal.', 'Record progress as you read.'],
    capabilities: ['Libraries and reading status', 'Reading progress', 'Book clubs and wish lists'],
    connections: ['Shared activity can appear in Corners.', 'Book wish items complement personal wish lists.'],
  },
  home_wiki: {
    purpose: 'A shared household reference for information people need to find again.',
    gettingStarted: ['Create a clearly named page.', 'Group related information into useful sections.'],
    capabilities: ['Shared reference pages', 'Household knowledge', 'Searchable information'],
    connections: ['Complements operational records in Home, Pets and Lists & Notes.', 'Can be disabled without deleting its information.'],
  },
  pets: {
    purpose: 'Track pet profiles, care, treatments and appointments.',
    gettingStarted: ['Create each pet profile.', 'Add recurring care and important health dates.'],
    capabilities: ['Pet profiles', 'Care schedules', 'Treatments and appointments'],
    connections: ['Dated care and appointments publish to Calendar and daily views.', 'Assignments can identify the responsible person.'],
  },
  homestead: {
    purpose: 'Organise rooms, maintenance, appliances, utilities and plans for the physical home.',
    gettingStarted: ['Add or link the rooms in your home.', 'Record maintenance, appliances and room projects where they belong.'],
    capabilities: ['Rooms and interactive floor plan', 'Maintenance and appliances', 'Room projects, utilities and household records'],
    connections: ['House-related bills remain managed in Money and are only viewed here.', 'Project items and activity can link into Corners.'],
  },
  meridian: {
    purpose: 'Household tasks, routines, rewards, goals and child-friendly wish requests.',
    gettingStarted: ['Create tasks or a recurring routine.', 'Assign them and choose the points or reward rules.'],
    capabilities: ['Tasks and routines', 'Points, goals and rewards', 'Wishlist approval'],
    connections: ['Assignments and completions appear in Corners.', 'Dated work can publish to Calendar and daily views.'],
  },
  fitness: {
    purpose: 'Build training programs, run workout sessions and track performance and personal bests.',
    gettingStarted: ['Choose or add exercises.', 'Build a program and assign it.', 'Start a session and complete sets as you train.'],
    capabilities: ['Exercise library and programs', 'Live, editable sessions', 'History, volume and personal records'],
    connections: ['Completed workouts and records appear in Corners with expandable details.', 'Activity links open the exact workout in Fitness history.'],
  },
  travel: {
    purpose: 'Plan trips and places to go, from an idea through bookings and departure.',
    gettingStarted: ['Save an idea in To go or create a trip.', 'Add travellers, dates, accommodation and transport.', 'Set booking deadlines before costs are due.'],
    capabilities: ['Trip ideas and full plans', 'Travellers, visibility and shared notes', 'Bookings, costs and deadlines'],
    connections: ['Trip and flight dates publish to Calendar.', 'Booking deadlines create identifiable Lists & Notes to-dos.'],
  },
  solace: {
    purpose: 'Manage household money through bills, pay cycles, buckets and payment history.',
    gettingStarted: ['Configure income and the current pay cycle.', 'Add bills, including subscriptions as a bill category.', 'Allocate available money without exceeding 100%.'],
    capabilities: ['Bills and payment history', 'Pay-cycle planning', 'Buckets, auto-pay and due alerts'],
    connections: ['Home-related costs can be viewed from Home without being managed twice.', 'Due information contributes to Dashboard and notifications.'],
  },
}

function guideFor(stack: StackDef): NodeGuide {
  const specific = details[stack.key]
  return {
    key: stack.key,
    label: stack.label,
    icon: stack.icon,
    colour: stack.colour,
    summary: stack.description,
    purpose: specific?.purpose ?? stack.description,
    gettingStarted: specific?.gettingStarted ?? ['Enable this node in Manage HomeStack.', 'Open it from navigation and add the first household record.'],
    capabilities: specific?.capabilities ?? [],
    connections: specific?.connections ?? [],
  }
}

const catalogueGuides: NodeGuide[] = [
  {
    key: 'inventory', label: 'Inventory', icon: '📦', colour: '#64748b', summary: 'Household stock, storage and replenishment',
    purpose: 'A planned capability for quantities, locations, expiry and low-stock reminders. The recommended roadmap places this inside Home as optional Stock & storage rather than another permanent destination.',
    gettingStarted: ['This capability is not ready for household use yet.', 'Review the Home consolidation proposal before enabling or entering real data.'],
    capabilities: ['Pantry and household consumables', 'Storage locations and quantities', 'Low-stock and expiry reminders'],
    connections: ['Would send replenishment items to Lists & Notes shopping lists.', 'Meals could read food stock later without owning it.'],
  },
  {
    key: 'assets', label: 'Assets', icon: '🧰', colour: '#64748b', summary: 'Valuables, vehicles, warranties and service history',
    purpose: 'A planned register for vehicles, tools, electronics, valuables and protected documents. Home appliances and warranties already belong to Home; the roadmap recommends an optional Assets & vehicles capability there.',
    gettingStarted: ['This capability is not ready for household use yet.', 'Use Home for current appliance, warranty and maintenance records.'],
    capabilities: ['Vehicle and equipment records', 'Registration and service history', 'Protected documents and valuations'],
    connections: ['Maintenance dates would publish to Calendar.', 'Financial payments remain owned by Money.'],
  },
  {
    key: 'hearth', label: 'Meals', icon: '🍲', colour: '#64748b', summary: 'Meals, recipes and household food planning',
    purpose: 'A future food-planning workspace for recipes, meal plans and reusable ingredient information, including safe recipe-link import after the product-link foundation.',
    gettingStarted: ['This node is not implemented yet.', 'Keep grocery lists in Lists & Notes until its source-owned meal workflow is built.'],
    capabilities: ['Recipe library', 'Meal planning', 'Recipe URL preview and ingredient review'],
    connections: ['Would send groceries to Lists & Notes.', 'Could read Home Stock & storage without copying inventory.'],
  },
  {
    key: 'projects', label: 'Projects', icon: '🛠️', colour: '#64748b', summary: 'General multi-step projects',
    purpose: 'A parked general-project concept. Home work belongs in Home, travel planning belongs in Travel and lightweight shared work belongs in Lists & Notes; enable a separate node only if a real workflow needs boards, dependencies or broad project budgets.',
    gettingStarted: ['This node is intentionally parked.', 'Use the owning node or a Lists & Notes list for current projects.'],
    capabilities: ['Potential boards and dependencies', 'Potential cross-domain project planning'],
    connections: ['Must not duplicate Home room projects or Travel trips.', 'Dated actions would publish through Calendar.'],
  },
  {
    key: 'health', label: 'Health', icon: '🩺', colour: '#64748b', summary: 'Private health records, care and appointments',
    purpose: 'A future sensitive node for personal health records, medication, care plans and appointments. It remains separate because its privacy and re-authentication boundary differs from Fitness.',
    gettingStarted: ['This node is not implemented yet.', 'Do not store sensitive medical detail in ordinary Lists & Notes notes while the protected workflow is unavailable.'],
    capabilities: ['Health profiles and care history', 'Medication and appointment tracking', 'Protected documents'],
    connections: ['Appointments would project safely to Calendar and Lists & Notes Agenda.', 'Fitness can share permitted high-level activity but must not absorb medical records.'],
  },
]

export const NODE_GUIDES: NodeGuide[] = [...STACKS.map(guideFor), ...catalogueGuides]
export const NODE_GUIDE_BY_KEY: Record<string, NodeGuide> = Object.fromEntries(NODE_GUIDES.map(guide => [guide.key, guide]))

export function fallbackNodeGuide(node: { key: string; name: string; description: string }): NodeGuide {
  return {
    key: node.key,
    label: node.name,
    icon: '◇',
    colour: '#64748b',
    summary: node.description,
    purpose: node.description,
    gettingStarted: ['Enable this node in Manage HomeStack.', 'Open it from navigation and configure it for your household.'],
    capabilities: [],
    connections: ['Disabled nodes keep their existing records and can be enabled again later.'],
  }
}
