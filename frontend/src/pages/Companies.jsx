import { useEffect, useState } from 'react'
import { ArrowUpRight, Search } from 'lucide-react'
import AppShell from '../components/AppShell'
import Button from '../components/Button'
import { Card, ErrorNote, FullPageSpinner } from '../components/ui'
import { api, ApiError } from '../lib/api'

export default function Companies() {
  const [query, setQuery] = useState('')
  const [companies, setCompanies] = useState(null)
  const [selected, setSelected] = useState(null)
  const [packs, setPacks] = useState([])
  const [sources, setSources] = useState([])
  const [packContent, setPackContent] = useState(null)
  const [error, setError] = useState('')

  async function search(searchQuery = query) {
    try {
      setCompanies(await api.companies(searchQuery))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not search company packs.')
      setCompanies([])
    }
  }

  useEffect(() => {
    let active = true
    api.companies('')
      .then((rows) => { if (active) setCompanies(rows) })
      .catch((err) => {
        if (!active) return
        setError(err instanceof ApiError ? err.message : 'Could not search company packs.')
        setCompanies([])
      })
    return () => { active = false }
  }, [])

  async function selectCompany(company) {
    setSelected(company)
    setPackContent(null)
    setError('')
    try {
      const [details, availablePacks] = await Promise.all([
        api.company(company.slug),
        api.companyPacks(company.slug),
      ])
      setSelected(details)
      setPacks(availablePacks)
      setSources(details.sources || [])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load company details.')
    }
  }

  async function startPack(pack) {
    setError('')
    try {
      const [content, packSources] = await Promise.all([
        api.startCompanyPack(pack.id),
        api.companyPackSources(pack.id),
      ])
      setPackContent(content)
      setSources(packSources)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start this practice pack.')
    }
  }

  function chooseAnswer(questionId, selectedAnswer) {
    setPackContent((current) => ({
      ...current,
      questions: current.questions.map((question) => question.id === questionId
        ? { ...question, selected_answer: selectedAnswer, is_correct: null, explanation: null }
        : question),
    }))
  }

  async function submitAnswer(question) {
    if (!question.selected_answer) return
    try {
      setError('')
      const response = await api.answerCompanyPackQuestion(packContent.pack_id, {
        question_id: question.id,
        selected_answer: question.selected_answer,
      })
      setPackContent((current) => ({
        ...current,
        completed: Boolean(response.completed_at),
        questions: current.questions.map((item) => item.id === question.id
          ? { ...item, ...response }
          : item),
      }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit this answer.')
    }
  }

  if (companies === null) return <FullPageSpinner />

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-semibold text-ink-900 mb-2">Company preparation</h1>
      <p className="text-sm text-ink-500 mb-6">Company facts are shown only with verified sources. Practice items are not actual or leaked company questions.</p>
      <ErrorNote>{error}</ErrorNote>
      <form className="flex gap-2 my-5" onSubmit={(event) => { event.preventDefault(); search() }}>
        <label className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search companies"
            className="w-full rounded-xl border border-ink-200 bg-paper-50 py-2.5 pl-9 pr-3 text-sm text-ink-900" />
        </label>
        <Button type="submit" onClick={() => setError('')}>Search</Button>
      </form>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-5">
        <div className="flex flex-col gap-2">
          {companies.length === 0 && (
            <Card className="p-5 text-sm text-ink-500">
              No verified company profiles are available yet. Packs appear after source-backed company information is reviewed and published.
            </Card>
          )}
          {companies.map((company) => (
            <button key={company.id} onClick={() => selectCompany(company)} className="text-left">
              <Card className={`p-4 hover:border-amber-500 ${selected?.id === company.id ? 'border-amber-500' : ''}`}>
                <h2 className="font-medium text-ink-900">{company.name}</h2>
                <p className="text-xs text-ink-500 mt-1">
                  {company.last_verified_at ? `Verified ${new Date(company.last_verified_at).toLocaleDateString()}` : 'Sources pending verification'}
                </p>
              </Card>
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          {selected && (
            <Card className="p-5">
              <h2 className="font-display text-xl font-semibold text-ink-900">{selected.name}</h2>
              {selected.facts_outdated && <p className="text-sm text-brick-600 mt-2">Previously verified information is outdated and hidden until it is re-verified.</p>}
              {selected.description && <p className="text-sm text-ink-600 mt-2">{selected.description}</p>}
              {selected.website && <a className="text-sm text-amber-600 inline-flex items-center gap-1 mt-2" href={selected.website} target="_blank" rel="noreferrer">Company website <ArrowUpRight size={14} /></a>}
              <h3 className="text-sm font-semibold text-ink-800 mt-5 mb-2">Practice packs</h3>
              {packs.length === 0 ? <p className="text-sm text-ink-500">No published packs yet.</p> : packs.map((pack) => (
                <div key={pack.id} className="border-t border-ink-200 py-3">
                  <p className="font-medium text-ink-900">{pack.title}</p>
                  <p className="text-xs text-ink-500">{pack.role} · version {pack.version}</p>
                  <p className="text-xs text-amber-600 mt-1">{pack.practice_content_notice}</p>
                  <Button size="sm" className="mt-2" onClick={() => startPack(pack)}>Start pack</Button>
                </div>
              ))}
            </Card>
          )}

          {packContent && (
            <Card className="p-5">
              <h2 className="font-display text-xl font-semibold text-ink-900">{packContent.title}</h2>
              <p className="text-xs text-amber-600 mt-1">{packContent.practice_content_notice}</p>
              {packContent.completed && <p className="text-sm text-moss-600 mt-2">Pack completed.</p>}
              {packContent.questions.length === 0 ? <p className="text-sm text-ink-500 mt-4">This pack has no available published practice items.</p> : packContent.questions.map((question) => (
                <article key={question.id} className="border-t border-ink-200 mt-4 pt-4">
                  <p className="text-xs text-ink-500">{question.topic} · {question.difficulty}</p>
                  <p className="text-sm text-ink-900 mt-1">{question.prompt}</p>
                  <div className="flex flex-col gap-2 mt-3">
                    {question.options.map((option, index) => {
                      const letter = 'ABCD'[index]
                      const selected = question.selected_answer === letter
                      return (
                        <button key={letter} onClick={() => chooseAnswer(question.id, letter)}
                          className={`rounded-lg border px-3 py-2 text-left text-sm ${selected ? 'border-ink-900 bg-ink-900 text-paper-50' : 'border-ink-200 text-ink-700'}`}>
                          {letter}. {option}
                        </button>
                      )
                    })}
                  </div>
                  {question.is_correct !== null && question.is_correct !== undefined && (
                    <p className={`text-sm mt-2 ${question.is_correct ? 'text-moss-600' : 'text-brick-600'}`}>
                      {question.is_correct ? 'Correct.' : 'Not quite.'} {question.explanation}
                    </p>
                  )}
                  <Button size="sm" className="mt-3" disabled={!question.selected_answer} onClick={() => submitAnswer(question)}>
                    Submit answer
                  </Button>
                </article>
              ))}
            </Card>
          )}

          {(sources.length > 0 || selected) && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink-800 mb-3">Verified sources</h2>
              {sources.length === 0 ? <p className="text-sm text-ink-500">No verified sources attached.</p> : sources.map((source) => (
                <a key={source.id || source.source_url} href={source.source_url} target="_blank" rel="noreferrer" className="block border-t border-ink-200 py-2 text-sm text-amber-600">
                  {source.source_title} <span className={`text-xs ${source.outdated ? 'text-brick-600' : 'text-ink-500'}`}>
                    ({source.source_type}, {source.outdated ? 'outdated · ' : 'verified '}
                    {source.verified_at ? new Date(source.verified_at).toLocaleDateString() : '—'})
                  </span>
                </a>
              ))}
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  )
}
