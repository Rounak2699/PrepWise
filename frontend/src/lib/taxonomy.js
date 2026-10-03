export const CATEGORY_STYLES = {
  quantitative: { label: 'Quantitative Aptitude', dot: 'bg-amber-500' },
  logical: { label: 'Logical Reasoning', dot: 'bg-amber-500' },
  verbal: { label: 'Verbal Ability', dot: 'bg-amber-500' },
  dsa: { label: 'Data Structures & Algorithms', dot: 'bg-ink-600' },
  oop: { label: 'Object-Oriented Programming', dot: 'bg-ink-600' },
  dbms: { label: 'Database Systems', dot: 'bg-ink-600' },
  os: { label: 'Operating Systems', dot: 'bg-ink-600' },
  networks: { label: 'Computer Networks', dot: 'bg-ink-600' },
  'software-eng': { label: 'Software Engineering', dot: 'bg-ink-600' },
}

export const ALL_TOPICS_BY_CATEGORY = {
  'Aptitude': ['quantitative', 'logical', 'verbal'],
  'Core CS': ['dsa', 'oop', 'dbms', 'os', 'networks', 'software-eng'],
}

export function categoryLabel(category) {
  return CATEGORY_STYLES[category]?.label || category
}

export function topicLabel(topic) {
  return topic.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
