import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  AcademicProfile, AcademicProfileResponse,
  AssessmentFile, AssessmentNote, AssessmentPriority, AssessmentStatus, AssessmentType,
  EducationAssessment, EducationClassSession, EducationCourse, EducationInstitution,
} from '../../../api/types'
import type { Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Tabs, type TabDef } from '../../../components/Tabs'
import { PageHeader } from '../../../components/PageHeader'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { useAuth } from '../../auth/AuthContext'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const inputCls =
  'w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink ' +
  'placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]'

const TYPE_LABELS: Record<AssessmentType, string> = {
  homework: 'Homework', assignment: 'Assignment', exam: 'Exam', quiz: 'Quiz',
  reading: 'Reading', project: 'Project', other: 'Other',
}
const STATUS_LABELS: Record<AssessmentStatus, string> = {
  todo: 'To do', in_progress: 'In progress', submitted: 'Submitted', done: 'Done',
}
const PRIORITY_TONE: Record<AssessmentPriority, string> = {
  high: 'bg-danger-soft text-danger', medium: 'bg-primary-soft text-primary',
  low: 'bg-sunken text-muted-strong',
}
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function dueLabel(iso: string | null, allDay = false) {
  if (!iso) return null
  const d = new Date(iso)
  const diff = Math.round((d.getTime() - Date.now()) / 86400000)
  const time = allDay ? '' : ` · ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
  if (diff < 0) return { text: `${Math.abs(diff)}d overdue`, tone: 'bg-danger-soft text-danger' }
  if (diff === 0) return { text: `Today${time}`, tone: 'bg-primary-soft text-primary' }
  if (diff === 1) return { text: `Tomorrow${time}`, tone: 'bg-sunken text-muted-strong' }
  return {
    text: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    tone: 'bg-sunken text-muted-strong',
  }
}

function fromInputValue(v: string): string | null {
  return v ? new Date(v).toISOString() : null
}
function calendarDayHref(iso: string | null) {
  return iso ? `/calendar?date=${new Date(iso).toISOString().slice(0, 10)}` : '/calendar'
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// ===========================================================================
// Assignment detail panel (notes + files)
// ===========================================================================

function AssessmentDetail({ assessment, onError }: {
  assessment: EducationAssessment
  onError: (m: string) => void
}) {
  const [notes, setNotes] = useState<AssessmentNote[]>([])
  const [files, setFiles] = useState<AssessmentFile[]>([])
  const [loadingNotes, setLoadingNotes] = useState(true)
  const [loadingFiles, setLoadingFiles] = useState(true)
  const [noteText, setNoteText] = useState('')
  const [addingNote, setAddingNote] = useState(false)
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null)
  const [editNoteText, setEditNoteText] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setLoadingNotes(true)
    setLoadingFiles(true)
    api.getAssessmentNotes(assessment.id)
      .then(setNotes).catch(e => onError(errMsg(e))).finally(() => setLoadingNotes(false))
    api.getAssessmentFiles(assessment.id)
      .then(setFiles).catch(e => onError(errMsg(e))).finally(() => setLoadingFiles(false))
  }, [assessment.id, onError])

  const addNote = async () => {
    if (!noteText.trim()) return
    setAddingNote(true)
    try {
      const note = await api.createAssessmentNote(assessment.id, noteText.trim())
      setNotes(prev => [...prev, note])
      setNoteText('')
    } catch (e) { onError(errMsg(e)) } finally { setAddingNote(false) }
  }

  const saveEdit = async (noteId: number) => {
    if (!editNoteText.trim()) return
    try {
      const updated = await api.updateAssessmentNote(assessment.id, noteId, editNoteText.trim())
      setNotes(prev => prev.map(n => n.id === noteId ? updated : n))
      setEditingNoteId(null)
    } catch (e) { onError(errMsg(e)) }
  }

  const deleteNote = async (noteId: number) => {
    try {
      await api.deleteAssessmentNote(assessment.id, noteId)
      setNotes(prev => prev.filter(n => n.id !== noteId))
    } catch (e) { onError(errMsg(e)) }
  }

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const uploaded = await api.uploadAssessmentFile(assessment.id, file)
      setFiles(prev => [...prev, uploaded])
    } catch (e) { onError(errMsg(e)) } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const deleteFile = async (fileId: number) => {
    if (!confirm('Remove this file?')) return
    try {
      await api.deleteAssessmentFile(assessment.id, fileId)
      setFiles(prev => prev.filter(f => f.id !== fileId))
    } catch (e) { onError(errMsg(e)) }
  }

  return (
    <div className="border-t border-line mt-2 pt-3 space-y-4">
      {/* Notes */}
      <div>
        <div className="text-xs font-semibold text-muted-strong uppercase tracking-wide mb-2">Notes</div>
        {loadingNotes ? (
          <p className="text-xs text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            {notes.map(note => (
              <div key={note.id} className="group relative bg-sunken rounded-xl px-3 py-2 text-sm text-ink">
                {editingNoteId === note.id ? (
                  <div className="space-y-2">
                    <textarea
                      autoFocus
                      className={`${inputCls} min-h-[72px] resize-none`}
                      value={editNoteText}
                      onChange={e => setEditNoteText(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button type="button" onClick={() => saveEdit(note.id)}>Save</Button>
                      <Button type="button" variant="ghost" onClick={() => setEditingNoteId(null)}>Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="whitespace-pre-wrap">{note.body}</p>
                    <div className="absolute top-2 right-2 hidden group-hover:flex gap-1">
                      <button
                        onClick={() => { setEditingNoteId(note.id); setEditNoteText(note.body) }}
                        className="text-muted hover:text-primary text-xs px-1.5 py-0.5 rounded"
                        aria-label="Edit note"
                      >edit</button>
                      <button
                        onClick={() => deleteNote(note.id)}
                        className="text-muted hover:text-danger text-lg leading-none px-1"
                        aria-label="Delete note"
                      >×</button>
                    </div>
                  </>
                )}
              </div>
            ))}
            <div className="flex gap-2 items-start">
              <textarea
                className={`${inputCls} min-h-[60px] resize-none flex-1`}
                placeholder="Add a note…"
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) addNote() }}
              />
              <Button type="button" onClick={addNote} loading={addingNote} variant="secondary">Add</Button>
            </div>
          </div>
        )}
      </div>

      {/* Files */}
      <div>
        <div className="text-xs font-semibold text-muted-strong uppercase tracking-wide mb-2">Files</div>
        {loadingFiles ? (
          <p className="text-xs text-muted">Loading…</p>
        ) : (
          <div className="space-y-1.5">
            {files.map(f => (
              <div key={f.id} className="group flex items-center gap-2 bg-sunken rounded-xl px-3 py-2">
                <a
                  href={f.file_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 min-w-0 text-sm text-primary hover:underline truncate"
                >
                  {f.label || f.original_filename}
                </a>
                {f.file_size > 0 && (
                  <span className="text-xs text-muted flex-shrink-0">{formatFileSize(f.file_size)}</span>
                )}
                <button
                  onClick={() => deleteFile(f.id)}
                  className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger text-lg leading-none flex-shrink-0 transition-opacity"
                  aria-label="Remove file"
                >×</button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                id={`file-upload-${assessment.id}`}
                className="sr-only"
                onChange={uploadFile}
                disabled={uploading}
              />
              <label
                htmlFor={`file-upload-${assessment.id}`}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-line text-sm text-muted-strong cursor-pointer hover:border-primary hover:text-primary transition-colors ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
              >
                {uploading ? 'Uploading…' : '+ Attach file'}
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ===========================================================================
// Assignments
// ===========================================================================

function AssignmentForm({ courses, people, defaultAssignee, onCreated, onError }: {
  courses: EducationCourse[]
  people: Person[]
  defaultAssignee: number | null
  onCreated: (a: EducationAssessment) => void
  onError: (m: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [type, setType] = useState<AssessmentType>('assignment')
  const [courseId, setCourseId] = useState('')
  const [due, setDue] = useState<string | null>(null)
  const [dueAllDay, setDueAllDay] = useState(true)
  const [priority, setPriority] = useState<AssessmentPriority>('medium')
  const [assignee, setAssignee] = useState<number | null>(defaultAssignee)
  const [busy, setBusy] = useState(false)

  // Sync assignee when people finish loading and defaultAssignee becomes available
  useEffect(() => {
    setAssignee(prev => prev ?? defaultAssignee)
  }, [defaultAssignee])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const a = await api.createAssessment({
        title: title.trim(), assessment_type: type, priority,
        course_id: courseId ? Number(courseId) : null,
        due_at: due, is_all_day: dueAllDay, assigned_to_person_id: assignee,
      })
      onCreated(a)
      setTitle(''); setDue(null); setDueAllDay(true); setCourseId(''); setType('assignment')
      setPriority('medium'); setAssignee(defaultAssignee)
      setOpen(false)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  if (!open) {
    return <Button variant="secondary" onClick={() => setOpen(true)}>+ Add assignment</Button>
  }
  return (
    <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
      <input autoFocus className={inputCls} placeholder="Assignment title" value={title}
        onChange={e => setTitle(e.target.value)} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <select className={inputCls} value={type} onChange={e => setType(e.target.value as AssessmentType)}>
          {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className={inputCls} value={courseId} onChange={e => setCourseId(e.target.value)}>
          <option value="">No course</option>
          {courses.map(c => <option key={c.id} value={c.id}>{c.code || c.name}</option>)}
        </select>
        <select className={inputCls} value={priority} onChange={e => setPriority(e.target.value as AssessmentPriority)}>
          <option value="low">Low priority</option>
          <option value="medium">Medium priority</option>
          <option value="high">High priority</option>
        </select>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-muted-strong mb-1">Due</div>
          <DateTimeField value={due} allDay={dueAllDay}
            onChange={({ value, allDay }) => { setDue(value); setDueAllDay(allDay) }} />
        </div>
        <div>
          <div className="text-xs text-muted-strong mb-1">Assign to</div>
          <AssigneeSelect people={people} value={assignee} onChange={setAssignee} className={inputCls} />
        </div>
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={busy}>Add</Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </form>
  )
}

function AssignmentRow({ a, onChange, onDelete, onError }: {
  a: EducationAssessment
  onChange: (a: EducationAssessment) => void
  onDelete: (id: number) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const due = dueLabel(a.due_at, a.is_all_day)

  const setStatus = async (status: AssessmentStatus) => {
    setBusy(true)
    try { onChange(await api.updateAssessment(a.id, { status })) }
    catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!confirm('Delete this assignment?')) return
    try { await api.deleteAssessment(a.id); onDelete(a.id) } catch (e) { onError(errMsg(e)) }
  }

  return (
    <li className="py-3 group">
      <div className="flex items-start gap-3">
        <button
          onClick={() => setStatus(a.is_complete ? 'todo' : 'done')}
          disabled={busy}
          className={`w-6 h-6 mt-0.5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${
            a.is_complete ? 'bg-success border-success text-white' : 'border-line-strong hover:border-success'
          }`}
          aria-label={a.is_complete ? 'Mark not done' : 'Mark done'}
        >
          {a.is_complete && <span className="text-xs">✓</span>}
        </button>

        <div className="flex-1 min-w-0">
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-left w-full"
          >
            <div className={`text-sm font-medium ${a.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
              {a.title}
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-1">
              <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">{TYPE_LABELS[a.assessment_type]}</span>
              {(a.course_code || a.course_name) && (
                <span className="text-xs text-muted">{a.course_code || a.course_name}</span>
              )}
              {!a.is_complete && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_TONE[a.priority]}`}>{a.priority}</span>}
              {due && (
                <Link
                  to={calendarDayHref(a.due_at)}
                  onClick={e => e.stopPropagation()}
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${due.tone}`}
                >
                  {due.text}
                </Link>
              )}
              <span className="text-xs text-muted-strong">{expanded ? '▲' : '▼'}</span>
            </div>
          </button>

          {expanded && (
            <AssessmentDetail assessment={a} onError={onError} />
          )}
        </div>

        <select
          value={a.status}
          onChange={e => setStatus(e.target.value as AssessmentStatus)}
          disabled={busy}
          className="text-xs rounded-lg border border-line bg-surface px-2 py-1 text-muted-strong flex-shrink-0"
        >
          {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <button onClick={remove} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none flex-shrink-0" aria-label="Delete">×</button>
      </div>
    </li>
  )
}

function AssignmentsTab({ courses, people, defaultAssignee, onError }: {
  courses: EducationCourse[]
  people: Person[]
  defaultAssignee: number | null
  onError: (m: string) => void
}) {
  const [assessments, setAssessments] = useState<EducationAssessment[]>([])
  const [showDone, setShowDone] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAssessments(showDone ? undefined : { open: true })
      .then(setAssessments).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [showDone, onError])

  const upsert = (a: EducationAssessment) =>
    setAssessments(prev => {
      const next = prev.some(x => x.id === a.id) ? prev.map(x => x.id === a.id ? a : x) : [...prev, a]
      if (!showDone && a.is_complete) return next.filter(x => x.id !== a.id)
      return next
    })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <AssignmentForm courses={courses} people={people} defaultAssignee={defaultAssignee} onCreated={upsert} onError={onError} />
        <label className="flex items-center gap-2 text-sm text-muted-strong">
          <input type="checkbox" checked={showDone} onChange={e => setShowDone(e.target.checked)} />
          Show completed
        </label>
      </div>
      <Card>
        {loading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : assessments.length === 0 ? (
          <p className="text-sm text-muted py-4 text-center">Nothing due. Add your first assignment above.</p>
        ) : (
          <ul className="divide-y divide-line">
            {assessments.map(a => (
              <AssignmentRow key={a.id} a={a} onChange={upsert} onDelete={id => setAssessments(prev => prev.filter(x => x.id !== id))} onError={onError} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

// ===========================================================================
// Courses
// ===========================================================================

function CoursesTab({ courses, reload, people, onError }: {
  courses: EducationCourse[]; reload: () => void; people: Person[]; onError: (m: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [teacher, setTeacher] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [creditValue, setCreditValue] = useState('6')
  const [studentId, setStudentId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      await api.createCourse({
        name: name.trim(), code: code.trim(), teacher: teacher.trim(),
        start_date: startDate || null, end_date: endDate || null,
        credit_value: Number(creditValue) || 0,
        student_id: studentId,
      })
      setName(''); setCode(''); setTeacher(''); setStartDate(''); setEndDate('')
      setCreditValue('6'); setStudentId(null); setOpen(false); reload()
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async (c: EducationCourse) => {
    if (!confirm(`Delete "${c.name}"? Its assignments stay but lose their course link.`)) return
    try { await api.deleteCourse(c.id); reload() } catch (e) { onError(errMsg(e)) }
  }

  const fmtDate = (d: string | null) => d ? new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : null

  return (
    <div className="space-y-4">
      {open ? (
        <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
          <input autoFocus className={inputCls} placeholder="Course/subject name" value={name} onChange={e => setName(e.target.value)} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input className={inputCls} placeholder="Code (e.g. COMP2041)" value={code} onChange={e => setCode(e.target.value)} />
            <input className={inputCls} placeholder="Lecturer / teacher" value={teacher} onChange={e => setTeacher(e.target.value)} />
            <label className="text-xs text-muted-strong flex flex-col gap-1">Start date
              <input type="date" className={inputCls} value={startDate} onChange={e => setStartDate(e.target.value)} />
            </label>
            <label className="text-xs text-muted-strong flex flex-col gap-1">End date
              <input type="date" className={inputCls} value={endDate} onChange={e => setEndDate(e.target.value)} />
            </label>
            <label className="text-xs text-muted-strong flex flex-col gap-1">Credit value (UOC)
              <input type="number" min={0} className={inputCls} value={creditValue} onChange={e => setCreditValue(e.target.value)} />
            </label>
            <div>
              <div className="text-xs text-muted-strong mb-1">Student</div>
              <AssigneeSelect people={people} value={studentId} onChange={setStudentId} className={inputCls} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>Add course</Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </form>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>+ Add course</Button>
      )}

      {courses.length === 0 ? (
        <Card><p className="text-sm text-muted py-4 text-center">No courses yet.</p></Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {courses.map(c => (
            <div key={c.id} className={`bg-surface rounded-2xl border p-4 group ${c.is_completed ? 'border-success/40 opacity-75' : 'border-line'}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className={`font-semibold truncate ${c.is_completed ? 'line-through text-muted' : 'text-ink'}`}>{c.name}</div>
                  {c.code && <div className="text-xs text-primary font-medium">{c.code}</div>}
                </div>
                <button onClick={() => remove(c)} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none" aria-label="Delete">×</button>
              </div>
              {c.teacher && <div className="text-sm text-muted mt-2">{c.teacher}</div>}
              {c.institution_name && <div className="text-xs text-muted mt-1">{c.institution_name}</div>}
              <div className="flex flex-wrap gap-2 mt-2">
                {(c.start_date || c.end_date) && (
                  <span className="text-xs text-muted">{fmtDate(c.start_date)}{c.end_date ? ` → ${fmtDate(c.end_date)}` : ''}</span>
                )}
                {c.credit_value > 0 && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${c.is_completed ? 'bg-success/10 text-success' : 'bg-primary-soft text-primary'}`}>{c.credit_value} UOC</span>
                )}
                {c.is_completed && <span className="text-xs text-success font-medium">✓ Complete</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Timetable
// ===========================================================================

function TimetableTab({ courses, onError }: { courses: EducationCourse[]; onError: (m: string) => void }) {
  const [sessions, setSessions] = useState<EducationClassSession[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('Lecture')
  const [courseId, setCourseId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [location, setLocation] = useState('')
  const [weekly, setWeekly] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.getClassSessions().then(setSessions).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [onError])

  const grouped = useMemo(() => {
    const by: Record<number, EducationClassSession[]> = {}
    for (const s of sessions) {
      const wd = new Date(s.start_at).getDay()
      ;(by[wd] ??= []).push(s)
    }
    for (const k of Object.keys(by)) {
      by[+k].sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    }
    return by
  }, [sessions])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!start) { onError('A start time is required.'); return }
    setBusy(true)
    try {
      const s = await api.createClassSession({
        title: title.trim(), course_id: courseId ? Number(courseId) : null,
        location: location.trim(), start_at: fromInputValue(start)!, end_at: fromInputValue(end),
        recurrence_rule: weekly ? 'FREQ=WEEKLY' : '',
      })
      setSessions(prev => [...prev, s])
      setStart(''); setEnd(''); setLocation(''); setCourseId(''); setTitle('Lecture'); setOpen(false)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async (s: EducationClassSession) => {
    if (!confirm('Delete this class from your timetable?')) return
    try { await api.deleteClassSession(s.id); setSessions(prev => prev.filter(x => x.id !== s.id)) }
    catch (e) { onError(errMsg(e)) }
  }

  return (
    <div className="space-y-4">
      {open ? (
        <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input autoFocus className={inputCls} placeholder="Label (e.g. Lecture, Tutorial)" value={title} onChange={e => setTitle(e.target.value)} />
            <select className={inputCls} value={courseId} onChange={e => setCourseId(e.target.value)}>
              <option value="">No course</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.code || c.name}</option>)}
            </select>
            <label className="text-xs text-muted-strong flex flex-col gap-1">Starts
              <input type="datetime-local" className={inputCls} value={start} onChange={e => setStart(e.target.value)} />
            </label>
            <label className="text-xs text-muted-strong flex flex-col gap-1">Ends
              <input type="datetime-local" className={inputCls} value={end} onChange={e => setEnd(e.target.value)} />
            </label>
            <input className={inputCls} placeholder="Location (room / building)" value={location} onChange={e => setLocation(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-strong">
            <input type="checkbox" checked={weekly} onChange={e => setWeekly(e.target.checked)} />
            Repeats weekly
          </label>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>Add class</Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </form>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>+ Add class</Button>
      )}

      {loading ? (
        <Card><p className="text-sm text-muted">Loading…</p></Card>
      ) : sessions.length === 0 ? (
        <Card><p className="text-sm text-muted py-4 text-center">No classes yet. Add your weekly lectures and tutorials.</p></Card>
      ) : (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5, 6, 0].filter(wd => grouped[wd]?.length).map(wd => (
            <Card key={wd} title={WEEKDAYS[wd] === 'Sun' ? 'Sunday' : ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][wd]}>
              <ul className="divide-y divide-line -mt-1">
                {grouped[wd].map(s => {
                  const t0 = new Date(s.start_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
                  const t1 = s.end_at ? new Date(s.end_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : null
                  return (
                    <li key={s.id} className="flex items-center gap-3 py-2.5 group">
                      <div className="text-sm font-medium text-primary w-28 flex-shrink-0">{t0}{t1 ? `–${t1}` : ''}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-ink truncate">{s.display_title}</div>
                        {s.location && <div className="text-xs text-muted">{s.location}</div>}
                      </div>
                      {s.recurrence_rule && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong flex-shrink-0">Weekly</span>}
                      <button onClick={() => remove(s)} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none flex-shrink-0" aria-label="Delete">×</button>
                    </li>
                  )
                })}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Academic Profile tab
// ===========================================================================

function CourseStatusCard({ label, courses, onToggleComplete }: {
  label: string
  courses: EducationCourse[]
  onToggleComplete: (c: EducationCourse) => void
}) {
  const [open, setOpen] = useState(true)
  if (courses.length === 0) return null
  return (
    <div className="bg-surface rounded-2xl border border-line p-4">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="font-semibold text-sm text-ink">{label}</span>
        <span className="text-muted text-xs">{courses.length} {open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <ul className="mt-3 divide-y divide-line">
          {courses.map(c => (
            <li key={c.id} className="py-2.5 flex items-center gap-3">
              <button
                onClick={() => onToggleComplete(c)}
                className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                  c.is_completed ? 'bg-success border-success text-white' : 'border-line-strong hover:border-success'
                }`}
                title={c.is_completed ? 'Mark incomplete' : 'Mark complete'}
              >
                {c.is_completed && <span className="text-xs">✓</span>}
              </button>
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium truncate ${c.is_completed ? 'line-through text-muted' : 'text-ink'}`}>
                  {c.code ? `${c.code} — ` : ''}{c.name}
                </div>
                <div className="flex flex-wrap gap-2 mt-0.5">
                  {c.start_date && (
                    <span className="text-xs text-muted">
                      {new Date(c.start_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      {c.end_date ? ` → ${new Date(c.end_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` : ''}
                    </span>
                  )}
                  {c.credit_value > 0 && (
                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary-soft text-primary font-medium">{c.credit_value} UOC</span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ProfileTab({ people, institutions, onInstitutionCreated, defaultPersonId, onError }: {
  people: Person[]
  institutions: EducationInstitution[]
  onInstitutionCreated: (i: EducationInstitution) => void
  defaultPersonId: number | null
  onError: (m: string) => void
}) {
  const [personId, setPersonId] = useState<number | null>(defaultPersonId)
  const [data, setData] = useState<AcademicProfileResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<Partial<AcademicProfile>>({})
  const [institutionInput, setInstitutionInput] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (defaultPersonId !== null) setPersonId(p => p ?? defaultPersonId)
  }, [defaultPersonId])

  useEffect(() => {
    if (!personId) return
    setLoading(true)
    api.getAcademicProfile(personId)
      .then(d => { setData(d); setForm(d.profile); setInstitutionInput(d.profile.institution_name ?? '') })
      .catch(e => onError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [personId, onError])

  const save = async () => {
    if (!personId || !data) return
    setSaving(true)
    try {
      // Resolve institution name → id (find existing or create new)
      let institutionId: number | null = form.institution_id ?? null
      const trimmed = institutionInput.trim()
      if (trimmed) {
        const existing = institutions.find(i => i.name.toLowerCase() === trimmed.toLowerCase())
        if (existing) {
          institutionId = existing.id
        } else {
          const created = await api.createInstitution({ name: trimmed })
          onInstitutionCreated(created)
          institutionId = created.id
        }
      } else {
        institutionId = null
      }

      const updated = await api.updateAcademicProfile(personId, {
        institution_id: institutionId,
        programme_name: form.programme_name ?? '',
        credits_required: form.credits_required ?? 0,
        credits_per_course_default: form.credits_per_course_default ?? 6,
        graduation_year: form.graduation_year ?? null,
        notes: form.notes ?? '',
      })
      setData(prev => prev ? { ...prev, profile: updated } : prev)
      setInstitutionInput(updated.institution_name ?? '')
      setEditing(false)
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  const toggleComplete = async (course: EducationCourse) => {
    if (!personId || !data) return
    try {
      await api.updateCourse(course.id, { is_completed: !course.is_completed })
      const refreshed = await api.getAcademicProfile(personId)
      setData(refreshed)
    } catch (e) { onError(errMsg(e)) }
  }

  const profile = data?.profile
  const credits = profile?.current_credits ?? 0
  const required = profile?.credits_required ?? 0
  const pct = required > 0 ? Math.min(100, Math.round((credits / required) * 100)) : 0

  if (people.length === 0 || loading) {
    return <Card><p className="text-sm text-muted">Loading profile…</p></Card>
  }

  return (
    <div className="space-y-4">
      {/* Person selector (in case multiple people in household) */}
      {people.length > 1 && (
        <select
          className={inputCls}
          value={personId ?? ''}
          onChange={e => setPersonId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Select person</option>
          {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
      )}

      {!personId ? (
        <Card><p className="text-sm text-muted py-4 text-center">Select a person to view their academic profile.</p></Card>
      ) : !profile ? (
        <Card><p className="text-sm text-muted">Loading…</p></Card>
      ) : (
        <>
          {/* Profile card */}
          <Card>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-bold text-ink text-lg">{profile.programme_name || 'Academic profile'}</div>
                {profile.institution_name && (
                  <div className="text-sm text-primary font-medium mt-0.5">{profile.institution_name}</div>
                )}
                {profile.graduation_year && (
                  <div className="text-xs text-muted mt-0.5">Expected graduation: {profile.graduation_year}</div>
                )}
              </div>
              <Button variant="ghost" onClick={() => setEditing(v => !v)}>
                {editing ? 'Cancel' : 'Edit'}
              </Button>
            </div>

            {editing && (
              <div className="mt-4 space-y-3 border-t border-line pt-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-muted-strong mb-1">Programme / degree</div>
                    <input className={inputCls} placeholder="e.g. B Eng (Computer Science)" value={form.programme_name ?? ''} onChange={e => setForm(f => ({ ...f, programme_name: e.target.value }))} />
                  </div>
                  <div>
                    <div className="text-xs text-muted-strong mb-1">Institution</div>
                    <input
                      className={inputCls}
                      list="institution-options"
                      placeholder="e.g. UNSW"
                      value={institutionInput}
                      onChange={e => setInstitutionInput(e.target.value)}
                    />
                    <datalist id="institution-options">
                      {institutions.map(i => <option key={i.id} value={i.name} />)}
                    </datalist>
                    {institutionInput.trim() && !institutions.some(i => i.name.toLowerCase() === institutionInput.trim().toLowerCase()) && (
                      <p className="text-xs text-muted mt-1">New institution "{institutionInput.trim()}" will be created on save.</p>
                    )}
                  </div>
                  <div>
                    <div className="text-xs text-muted-strong mb-1">Credits required to graduate (UOC)</div>
                    <input type="number" min={0} className={inputCls} value={form.credits_required ?? 0} onChange={e => setForm(f => ({ ...f, credits_required: Number(e.target.value) }))} />
                  </div>
                  <div>
                    <div className="text-xs text-muted-strong mb-1">Default credits per course (UOC)</div>
                    <input type="number" min={0} className={inputCls} value={form.credits_per_course_default ?? 6} onChange={e => setForm(f => ({ ...f, credits_per_course_default: Number(e.target.value) }))} />
                  </div>
                  <div>
                    <div className="text-xs text-muted-strong mb-1">Graduation year</div>
                    <input type="number" min={2020} max={2040} className={inputCls} placeholder="e.g. 2027" value={form.graduation_year ?? ''} onChange={e => setForm(f => ({ ...f, graduation_year: e.target.value ? Number(e.target.value) : null }))} />
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-strong mb-1">Notes</div>
                  <textarea className={`${inputCls} min-h-[64px] resize-none`} value={form.notes ?? ''} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                </div>
                <Button onClick={save} loading={saving}>Save profile</Button>
              </div>
            )}

            {/* Credit progress */}
            {required > 0 && (
              <div className="mt-4 border-t border-line pt-4">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="font-medium text-ink">Credit progress</span>
                  <span className="text-muted-strong">{credits} / {required} UOC ({pct}%)</span>
                </div>
                <div className="h-3 bg-sunken rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {pct >= 100 && (
                  <p className="text-sm text-success font-semibold mt-2">All credits complete — eligible to graduate!</p>
                )}
              </div>
            )}
          </Card>

          {/* Course buckets */}
          {data && (
            <div className="space-y-3">
              <CourseStatusCard
                label="Current modules"
                courses={data.courses.current}
                onToggleComplete={toggleComplete}
              />
              <CourseStatusCard
                label="Upcoming modules"
                courses={data.courses.upcoming}
                onToggleComplete={toggleComplete}
              />
              {data.courses.past.length > 0 && (
                <details className="bg-surface rounded-2xl border border-line">
                  <summary className="px-4 py-3 text-sm font-semibold text-muted-strong cursor-pointer">
                    Completed / past modules ({data.courses.past.length})
                  </summary>
                  <div className="px-4 pb-4">
                    <CourseStatusCard
                      label=""
                      courses={data.courses.past}
                      onToggleComplete={toggleComplete}
                    />
                  </div>
                </details>
              )}
              {data.courses.current.length === 0 && data.courses.upcoming.length === 0 && data.courses.past.length === 0 && (
                <Card>
                  <p className="text-sm text-muted py-2 text-center">
                    No courses assigned to this person yet. Add courses in the Courses tab and set this person as the student.
                  </p>
                </Card>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ===========================================================================
// Page
// ===========================================================================

type Tab = 'profile' | 'assignments' | 'courses' | 'timetable'

const TABS: TabDef<Tab>[] = [
  { key: 'profile', label: 'My Profile' },
  { key: 'assignments', label: 'Assignments' },
  { key: 'courses', label: 'Courses' },
  { key: 'timetable', label: 'Timetable' },
]

export function EducationPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('profile')
  const [courses, setCourses] = useState<EducationCourse[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [institutions, setInstitutions] = useState<EducationInstitution[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadCourses = () => api.getCourses().then(setCourses).catch(e => setError(errMsg(e)))
  useEffect(() => { loadCourses() }, [])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])
  useEffect(() => { api.getInstitutions().then(setInstitutions).catch(() => {}) }, [])

  const defaultAssignee = personIdForUser(people, user?.id)

  return (
    <div className="space-y-5 max-w-3xl mx-auto">
      <PageHeader title="Education" icon="🎓" subtitle="Your courses, deadlines and weekly timetable." />

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'profile' && <ProfileTab people={people} institutions={institutions} onInstitutionCreated={i => setInstitutions(prev => [...prev, i])} defaultPersonId={defaultAssignee} onError={setError} />}
      {tab === 'assignments' && <AssignmentsTab courses={courses} people={people} defaultAssignee={defaultAssignee} onError={setError} />}
      {tab === 'courses' && <CoursesTab courses={courses} reload={loadCourses} people={people} onError={setError} />}
      {tab === 'timetable' && <TimetableTab courses={courses} onError={setError} />}
    </div>
  )
}
