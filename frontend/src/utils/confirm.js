import { ElMessageBox } from 'element-plus'

/**
 * 危险操作统一确认框。
 *
 * 为什么要统一：原先各处风格不一——有的只有一句 `ElMessageBox.confirm('确认删除？')`，
 * 有的干脆直接执行（移除重点人员、签收派单都是「点了就改数据」）。演示时误点一下
 * 数据就变了，且没有任何挽回余地。
 *
 * 文案结构固定为「做什么 + 什么后果」，比单句「确认删除？」更能防误触。
 *
 * @param {object}   opts
 * @param {string}   opts.action       动作短语，如「移除重点人员 张*明」
 * @param {string}   [opts.title]      标题
 * @param {string}   [opts.detail]     后果说明（会换行显示在动作下方）
 * @param {string}   [opts.confirmText] 确认按钮文案
 * @param {string}   [opts.type]       Element 图标类型：warning / error / info
 * @returns {Promise<boolean>} 确认返回 true；取消或关闭返回 false（**不抛异常**）
 */
export async function confirmDanger({
  action,
  title = '操作确认',
  detail = '',
  confirmText = '确认执行',
  type = 'warning'
} = {}) {
  const message = detail
    ? `<div style="line-height:1.7">确认${esc(action)}？</div>` +
      `<div style="margin-top:8px;opacity:.72;font-size:13px;line-height:1.7">${esc(detail)}</div>`
    : `确认${esc(action)}？`

  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: confirmText,
      cancelButtonText: '取消',
      type,
      // 点遮罩不当作取消，避免误触关闭后以为已执行
      closeOnClickModal: false,
      distinguishCancelAndClose: true,
      // action/detail 里可能带用户名等动态值，esc() 已转义
      dangerouslyUseHTMLString: true
    })
    return true
  } catch {
    return false
  }
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

export default confirmDanger
