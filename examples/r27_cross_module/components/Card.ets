
import { Button } from './Button'

@Component
export struct Card {
  @Prop title: string = ''
  @Prop content: string = ''
  
  build() {
    Column() {
      Text(this.title)
      Text(this.content)
      Button({ label: 'OK' })
    }
  }
}
