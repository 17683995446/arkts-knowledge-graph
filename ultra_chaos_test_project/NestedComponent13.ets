/**
 * 嵌套组件文件 - 深度 13
 */

import { NestedComponent14 } from './NestedComponent14';

@Component
export struct NestedComponent13 {
    build() {
        Column() {
            NestedComponent14()
            NestedComponent14()
        }
    }
}
