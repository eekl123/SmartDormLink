import { DeviceState, Rule, formatActions, formatConditions } from '../domain/DormLinkDomain';

/** 规则卡片：条件、动作、优先级、启停与编辑入口 */
@Component
export struct RuleCard {
  @Prop rule: Rule;
  @Prop devices: DeviceState[];
  onToggle: (id: string, enabled: boolean) => void = () => {};
  onEdit: (id: string) => void = () => {};
  onDelete: (id: string) => void = () => {};

  private priorityColor(): string {
    if (this.rule.priority >= 8) {
      return '#E5484D';
    }
    if (this.rule.priority >= 5) {
      return '#F5A524';
    }
    return '#12A594';
  }

  build() {
    Column({ space: 6 }) {
      Row() {
        Text(`P${this.rule.priority}`)
          .fontSize(11)
          .fontColor('#FFFFFF')
          .backgroundColor(this.priorityColor())
          .borderRadius(6)
          .padding({ left: 6, right: 6, top: 2, bottom: 2 })
        Text(this.rule.name)
          .fontSize(15)
          .fontWeight(FontWeight.Medium)
          .fontColor(this.rule.enabled ? '#1A1D26' : '#A8ADBC')
          .layoutWeight(1)
          .margin({ left: 8 })
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Toggle({ type: ToggleType.Switch, isOn: this.rule.enabled })
          .selectedColor('#2F6BFF')
          .onChange((isOn: boolean) => {
            this.onToggle(this.rule.id, isOn);
          })
      }
      .width('100%')

      Text(`当 ${formatConditions(this.rule)}`)
        .fontSize(12)
        .fontColor('#4A5163')
        .width('100%')
        .maxLines(2)

      Text(`执行 ${formatActions(this.rule, this.devices)}`)
        .fontSize(12)
        .fontColor('#2F6BFF')
        .width('100%')
        .maxLines(2)

      Row({ space: 10 }) {
        Text(this.rule.cooldownSec > 0 ? `冷却 ${this.rule.cooldownSec}s` : '无冷却')
          .fontSize(11)
          .fontColor('#8A90A2')
        Blank()
        Button('编辑')
          .fontSize(12)
          .height(28)
          .backgroundColor('#EEF2FF')
          .fontColor('#2F6BFF')
          .onClick(() => {
            this.onEdit(this.rule.id);
          })
        Button('删除')
          .fontSize(12)
          .height(28)
          .backgroundColor('#FDECEC')
          .fontColor('#E5484D')
          .onClick(() => {
            this.onDelete(this.rule.id);
          })
      }
      .width('100%')
    }
    .width('100%')
    .padding(14)
    .borderRadius(14)
    .backgroundColor('#FFFFFF')
    .shadow({ radius: 12, color: '#0F1A3D12', offsetY: 4 })
  }
}
