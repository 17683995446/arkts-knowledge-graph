/**
 * 嵌套组件文件 - 深度 14
 */

import { NestedComponent15 } from './NestedComponentFile15';

@Component
export struct NestedComponent14 {

    build() {
        Column() {
            NestedComponent15()
            NestedComponent15()
            NestedComponent15()
        }
    }

}
