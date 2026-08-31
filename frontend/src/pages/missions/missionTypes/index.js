import multipleChoice from './multipleChoice'
import promptRanking from './promptRanking'
import promptSelection from './promptSelection'
import singleChoice from './singleChoice'
import aiChatChallenge from './aiChatChallenge'
import bulkCategorization from './bulkCategorization'
import planActualDeviation from './planActualDeviation'
import duplicatePaymentHunt from './duplicatePaymentHunt'
import invoiceExtraction from './invoiceExtraction'
import policyViolationCheck from './policyViolationCheck'
import receivablesAging from './receivablesAging'
import vatRateAudit from './vatRateAudit'
import bankReconciliation from './bankReconciliation'

export const quizMissionTypes = [singleChoice, multipleChoice, promptSelection, promptRanking]
export const taskChallengeTypes = [bulkCategorization, planActualDeviation, duplicatePaymentHunt, invoiceExtraction, policyViolationCheck, receivablesAging, vatRateAudit, bankReconciliation]
// Every scheduled mission type is editable in Manage Missions. The chat challenge remains training-only.
export const missionTypes = [...quizMissionTypes, ...taskChallengeTypes]
export const trainingMissionTypes = [...quizMissionTypes, aiChatChallenge, ...taskChallengeTypes]
export const missionTypeRegistry = Object.fromEntries(trainingMissionTypes.map((definition) => [definition.id, definition]))
export const defaultMissionType = singleChoice.id

export function getMissionType(type) {
  return missionTypeRegistry[type] || singleChoice
}

export function createMissionTypeDefaults() {
  return {
    ...singleChoice.createDefaults(),
    ...bulkCategorization.createDefaults(),
    correct_order: [0, 1, 2],
  }
}
