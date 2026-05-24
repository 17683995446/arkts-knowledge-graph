/**
 * 嵌套组件文件 - 深度 18
 */

import { NestedComponent19 } from './NestedComponent19';

@Component
export struct NestedComponent18 {
    build() {
        Column() {
            NestedComponent19()
            NestedComponent19()
        }
    }
}
