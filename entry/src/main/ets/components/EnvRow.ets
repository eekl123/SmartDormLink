import { MetricMeta } from '../domain/DormLinkDomain';

/** 环境量滑块行：温度 / 湿度 / 光照 */
@Component
export struct EnvRow {
  @Prop meta: MetricMeta;
  @Prop value: number;
  onValueChange: (key: string, value: number) => void = () => {};

  build() {
    Column({ space: 4 }) {
      Row() {
        Text(this.meta.label).fontSize(13).fontColor('#4A5163')
        Blank()
        Text(`${this.value}${this.meta.unit}`)
          .fontSize(13)
          .fontWeight(FontWeight.Medium)
          .fontColor('#2F6BFF')
      }
      .width('100%')

      Slider({
        value: this.value,
        min: this.meta.min,
        max: this.meta.max,
        step: this.meta.step,
        style: SliderStyle.OutSet
      })
        .selectedColor('#2F6BFF')
        .trackColor('#E7EAF3')
        .onChange((value: number, mode: SliderChangeMode) => {
          this.onValueChange(this.meta.key, value);
        })
    }
    .width('100%')
  }
}
