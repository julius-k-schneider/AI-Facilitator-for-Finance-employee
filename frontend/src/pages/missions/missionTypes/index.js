import complianceDecision from './complianceDecision'
import complianceTrafficLight from './complianceTrafficLight'
import multipleChoice from './multipleChoice'
import promptRanking from './promptRanking'
import promptSelection from './promptSelection'
import singleChoice from './singleChoice'
import aiChatChallenge from './aiChatChallenge'
import bulkCategorization from './bulkCategorization'
import planActualDeviation from './planActualDeviation'
import duplicatePaymentHunt from './duplicatePaymentHunt'
import invoiceExtraction from './invoiceExtraction'

// Hand-authorable quiz types offered in the manual creator editor.
export const missionTypes = [singleChoice, multipleChoice, complianceDecision, promptSelection, promptRanking, complianceTrafficLight]
// Task challenge types are AI-generated only (no manual editor) but appear in the daily, schedule, and training flows.
export const taskChallengeTypes = [bulkCategorization, planActualDeviation, duplicatePaymentHunt, invoiceExtraction]
export const trainingMissionTypes = [...missionTypes, aiChatChallenge, ...taskChallengeTypes]
export const missionTypeRegistry = Object.fromEntries(trainingMissionTypes.map((definition) => [definition.id, definition]))
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
