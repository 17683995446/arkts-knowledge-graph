
import { List } from './List'
import { Button } from './Button'

@Entry
@Component
struct Page {
  @State data: string[] = ['A', 'B', 'C']
  
  build() {
    Column() {
      List({ items: this.data })
      Button({ label: 'Refresh' })
    }
  }
}
