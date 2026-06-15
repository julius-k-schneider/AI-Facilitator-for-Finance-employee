import complianceDecision from './complianceDecision'
import complianceTrafficLight from './complianceTrafficLight'
import multipleChoice from './multipleChoice'
import promptRanking from './promptRanking'
import promptSelection from './promptSelection'
import singleChoice from './singleChoice'

export const missionTypes = [singleChoice, multipleChoice, complianceDecision, promptSelection, promptRanking, complianceTrafficLight]
export const missionTypeRegistry = Object.fromEntries(missionTypes.map((definition) => [definition.id, definition]))
export const defaultMissionType = singleChoice.id

export function getMissionType(type) {
  return missionTypeRegistry[type] || singleChoice
}

export function createMissionTypeDefaults() {
  return {
    ...singleChoice.createDefaults(),
    ...complianceTrafficLight.createDefaults(),
    correct_order: [0, 1, 2],
  }
}

export function createTestMissions(language) {
  const text = (de, en) => language === 'en' ? en : de
  return missionTypes.map((definition) => definition.example(text))
}
